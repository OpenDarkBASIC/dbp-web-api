cmake_minimum_required (VERSION 3.3)

project ("stdout-plugin"
	LANGUAGES CXX RC
	VERSION 0.0.1)

add_library (stdout-plugin SHARED
	"src/plugin.cpp"
	"src/plugin.rc")
