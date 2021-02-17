import json
import quart
import asyncio
import os
import sys
import traceback
import tempfile
import mmap


if not os.path.exists("config.json"):
    open("config.json", "wb").write(json.dumps({
        "server": {
            "host": "0.0.0.0",
            "port": 8014
        },
        "dbp": {
            "path": "<path to Dark Basic Professional (Online) root directory>",
            "compiler_timeout": 3,
            "program_timeout": 5
        }
    }, indent=2).encode("utf-8"))
    print("Created file config.json. Please edit it with the correct settings now, then run the script again")
    sys.exit(1)


config = json.loads(open("config.json", "rb").read().decode("utf-8"))
app = quart.Quart(__name__)
compiler_lock = asyncio.Lock()


def line_endings_to_dos(code):
    return code.replace("\r", "").replace("\n", "\r\n")


def line_endings_to_unix(code):
    return code.replace("\r", "")


async def compile_dbp_source(code):
    compiler = os.path.join(config["dbp"]["path"], "Compiler", "DBPCompiler.exe")
    async with compiler_lock:
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "source.dba"), "wb") as f:
                f.write(code.encode("utf-8"))

            mm = mmap.mmap(0, 256, "DBPROEDITORMESSAGE")
            compiler_process = await asyncio.create_subprocess_exec(compiler, "source.dba", cwd=tmpdir)
            try:
                await asyncio.wait_for(compiler_process.wait(), config["dbp"]["compiler_timeout"])
            except asyncio.TimeoutError:
                error_msg = mm.read().decode("utf-8").strip("\r\n\0")
                compiler_process.terminate()
                await asyncio.sleep(1)  # have to wait for the process to actually terminate, or windows won't delete tmpdir
                return False, error_msg

            if not os.path.exists(os.path.join(tmpdir, "default.exe")):
                error_msg = mm.read().decode("utf-8").strip("\r\n\0")
                await asyncio.sleep(1)  # have to wait for the process to actually terminate, or windows won't delete tmpdir
                return False, error_msg

            program_process = await asyncio.create_subprocess_exec(
                os.path.join(tmpdir, "default.exe"),
                stdout=asyncio.subprocess.PIPE,
                cwd=tmpdir)
            try:
                await asyncio.wait_for(program_process.wait(), config["dbp"]["program_timeout"])
                out = await program_process.stdout.read()
                return True, out.decode("utf-8")
            except asyncio.TimeoutError:
                program_process.terminate()
                await asyncio.sleep(1)  # have to wait for the process to actually terminate, or windows won't delete tmpdir
                return False, f"Executable didn't terminate after {config['dbp']['program_timeout']}s"


@app.route("/update")
async def do_update():
    return {
        "success": True,
        "message": ""
    }


@app.route("/commit_hash")
async def commit_hash():
    return {
        "commit_hash": "0"
    }


@app.route("/compile", methods=["POST"])
async def do_compile():
    payload = await quart.request.get_data()
    snippet = json.loads(payload.decode("utf-8"))
    code = line_endings_to_dos(snippet["code"])
    success, output = await compile_dbp_source(code)
    return {
        "success": success,
        "output": line_endings_to_unix(output)
    }


@app.route("/compile_multi", methods=["POST"])
async def do_compile_multi():
    payload = await quart.request.get_data()
    code_snippets = json.loads(payload.decode("utf-8"))

    results = list()
    for snippet in code_snippets:
        code = line_endings_to_dos(snippet["code"])
        success, output = await compile_dbp_source(code)
        results.append({
            "success": success,
            "output": line_endings_to_unix(output)
        })

    return quart.jsonify(results)


loop = asyncio.get_event_loop()
try:
    app.run(loop=loop, host=config["server"]["host"], port=config["server"]["port"])
except KeyboardInterrupt:
    pass
except:
    traceback.print_exc()
finally:
    loop.close()
