import json
import quart
import asyncio
import os
import sys
import traceback
import tempfile
import mmap
import hmac
import hashlib

if not os.path.exists("config.json"):
    open("config.json", "wb").write(json.dumps({
        "server": {
            "port": 8080,
            "secret": "token"
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


def verify_signature(payload, signature):
    payload_signature = hmac.new(
        key=config["server"]["secret"].encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256).hexdigest()
    return hmac.compare_digest(payload_signature, signature)


@app.route("/")
async def index():
    return "hello"


@app.route("/v1/compile", methods=["POST"])
async def compile_v1():
    payload = await quart.request.get_data()
    if not verify_signature(payload, quart.request.headers["X-Signature-256"].replace("sha256=", "")):
        quart.abort(403)

    success, output = await compile_dbp_source_v1(json.loads(payload.decode("utf-8")))
    return {
        "success": success,
        "output": output
    }


async def compile_dbp_source_v1(payload):
    compiler = os.path.join(config["dbp"]["path"], "Compiler", "DBPCompiler.exe")
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "source.dba"), "wb") as f:
            f.write(payload["code"].encode("utf-8"))

        mm = mmap.mmap(0, 256, "DBPROEDITORMESSAGE")
        compiler_process = await asyncio.create_subprocess_exec(compiler, "source.dba", cwd=tmpdir)
        try:
            await asyncio.wait_for(compiler_process.wait(), config["dbp"]["compiler_timeout"])
        except asyncio.TimeoutError:
            error_msg = mm.read().decode("utf-8")
            compiler_process.terminate()
            await asyncio.sleep(2)  # have to wait for the process to actually terminate, or windows won't delete tmpdir
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
            await asyncio.sleep(2)  # have to wait for the process to actually terminate, or windows won't delete tmpdir
            return False, f"Executable didn't terminate after {config['dbp']['program_timeout']}s"


loop = asyncio.get_event_loop()
try:
    app.run(loop=loop, port=config["server"]["port"])
except KeyboardInterrupt:
    pass
except:
    traceback.print_exc()
finally:
    loop.close()
