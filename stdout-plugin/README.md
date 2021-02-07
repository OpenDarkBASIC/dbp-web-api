Build with:

```
mkdir build && cd build
cmake -A win32 ../
cmake --build . --config Release
```

Then copy the resulting dll from ```build/Release/stdout-plugin.dll``` to ```<DBP root>/Compiler/plugins-user```.

