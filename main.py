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
            "port": 8080
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


@app.route("/")
async def index():
    return "hello world"


async def compile_dbp_source(payload):
    compiler = os.path.join(config["dbp"]["path"], "Compiler", "DBPCompiler.exe")
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "source.dba"), "wb") as f:
            f.write(payload["code"].encode("utf-8"))

        mm = mmap.mmap(0, 256, "DBPROEDITORMESSAGE")
        compiler_process = await asyncio.create_subprocess_exec(compiler, "source.dba", cwd=tmpdir)
        try:
            await asyncio.wait_for(compiler_process.wait(), config["dbp"]["compiler_timeout"])
        except asyncio.TimeoutError:
            print(mm.read().decode("utf-8"))
            compiler_process.terminate()
            await asyncio.sleep(2)
            return

        program_process = await asyncio.create_subprocess_exec(os.path.join(tmpdir, "default.exe"), cwd=tmpdir)
        try:
            await asyncio.wait_for(program_process.wait(), config["dbp"]["program_timeout"])
        except asyncio.TimeoutError:
            program_process.terminate()
            await asyncio.sleep(2)
            return


loop = asyncio.get_event_loop()
try:
    payload = dict(code="print stdout \"hello\"\n")
    loop.run_until_complete(compile_dbp_source(payload))
    #app.run(loop=loop, port=config["port"])
except KeyboardInterrupt:
    pass
except:
    traceback.print_exc()
finally:
    loop.close()
