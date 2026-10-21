# SPDX-License-Identifier: MIT
# Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
#
# Engine side of the numerical studies (see README.md): one executable per
# problem folder, each linked to the physics-engine library only.
cmake_minimum_required(VERSION 3.20)
project(landau_simulations LANGUAGES CXX)

set(PHYSICS_ENGINE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../physics-engine/engine"
    CACHE PATH "Path to the engine/ directory of the physics-engine submodule")
add_subdirectory("${PHYSICS_ENGINE_DIR}" physics-engine EXCLUDE_FROM_ALL)

# add_study(S5P1) builds S5P1/engine.cpp into the executable S5P1
function(add_study name)
    add_executable(${name} ${name}/engine.cpp)
    target_include_directories(${name} PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
    target_link_libraries(${name} PRIVATE physics::engine)
    set_target_properties(${name} PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
    # MinGW: a static runtime, so that another libstdc++-6.dll on PATH (e.g.
    # Git for Windows') is not loaded instead, which breaks the CSV output
    if(MINGW)
        target_link_options(${name} PRIVATE -static)
    endif()
endfunction()

add_study(S5P1)
add_study(S5P2)
add_study(S5P3a)
add_study(S5P3b)
add_study(S5P3c)
add_study(S5P4)
add_study(S7P1)
add_study(S10P1)
add_study(S10P2)
