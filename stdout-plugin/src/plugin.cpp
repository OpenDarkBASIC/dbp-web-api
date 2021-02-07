#include <stdio.h>
#include "wtypes.h"

#define EXPORT __declspec(dllexport)
#define EXPORTC extern "C" __declspec(dllexport)

EXPORT void ReceiveCoreDataPtr(void* InCorePtr)
{
}
EXPORT void PreDestructor(void)
{
}
EXPORT void Destructor(void)
{
}

EXPORTC void print_stdout(LPSTR pString)
{
    puts(pString);
}
