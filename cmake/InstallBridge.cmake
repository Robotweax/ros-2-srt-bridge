include(GNUInstallDirs)
include(CMakePackageConfigHelpers)
get_filename_component(_bridge_root "${CMAKE_CURRENT_LIST_DIR}/.." ABSOLUTE)
set(_bridge_features core)
set(_bridge_targets robotweax_srt_bridge_core)
set_target_properties(robotweax_srt_bridge_core PROPERTIES EXPORT_NAME core)
foreach(_pair "management|protocol" "journal|journal" "worker|worker" "worker_runtime|worker_runtime" "transport|transport" "endpoint|endpoint")
  string(REPLACE "|" ";" _parts "${_pair}")
  list(GET _parts 0 _suffix)
  list(GET _parts 1 _name)
  set(_target robotweax_srt_bridge_${_suffix})
  if(TARGET ${_target})
    set_target_properties(${_target} PROPERTIES EXPORT_NAME ${_name})
    list(APPEND _bridge_targets ${_target})
    list(APPEND _bridge_features ${_name})
  endif()
endforeach()
if(TARGET robotweax-journal-worker)
  set_target_properties(robotweax-journal-worker PROPERTIES EXPORT_NAME journal_worker)
  list(APPEND _bridge_targets robotweax-journal-worker)
endif()
install(TARGETS ${_bridge_targets} EXPORT RobotweaxBridgeTargets
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
  RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
install(DIRECTORY "${_bridge_root}/src/robotweax_srt_bridge_core/include/"
  DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(DIRECTORY "${_bridge_root}/proto/" DESTINATION ${CMAKE_INSTALL_DATADIR}/robotweax-srt-bridge/proto
  FILES_MATCHING PATTERN "*.proto")
set(_bridge_package_dir ${CMAKE_INSTALL_LIBDIR}/cmake/RobotweaxBridge)
configure_package_config_file("${CMAKE_CURRENT_LIST_DIR}/RobotweaxBridgeConfig.cmake.in"
  "${CMAKE_CURRENT_BINARY_DIR}/RobotweaxBridgeConfig.cmake"
  INSTALL_DESTINATION ${_bridge_package_dir})
write_basic_package_version_file("${CMAKE_CURRENT_BINARY_DIR}/RobotweaxBridgeConfigVersion.cmake"
  VERSION ${PROJECT_VERSION} COMPATIBILITY SameMinorVersion)
install(EXPORT RobotweaxBridgeTargets NAMESPACE RobotweaxBridge:: DESTINATION ${_bridge_package_dir})
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/RobotweaxBridgeConfig.cmake"
  "${CMAKE_CURRENT_BINARY_DIR}/RobotweaxBridgeConfigVersion.cmake" DESTINATION ${_bridge_package_dir})
