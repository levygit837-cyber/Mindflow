#include <flutter/dart_project.h>
#include <flutter/flutter_view_controller.h>
#include <windows.h>

#include "resource.h"
#include "utils.h"
#include "window_configuration.h"

int APIENTRY wWinMain(HINSTANCE instance, HINSTANCE prev, wchar_t* command_line, int show_command) {
  // Attach to console when present
  if (::AttachConsole(ATTACH_PARENT_PROCESS) || ::AllocConsole()) {
    FILE* unused;
    freopen_s(&unused, "CONOUT$", "w", stdout);
    freopen_s(&unused, "CONOUT$", "w", stderr);
  }

  // Replace this with the path to your flutter_desktop folder
  flutter::DartProject project(L"C:\\path\\to\\flutter_desktop");

  flutter::FlutterViewController controller(
    flutter::FlutterViewController::kDefaultWindowSize,
    project);

  // Create window
  HWND window = CreateWindow(
    L"MindFlow", L"MindFlow",
    WS_OVERLAPPEDWINDOW | WS_VISIBLE,
    CW_USEDEFAULT, CW_USEDEFAULT,
    1280, 800,
    nullptr, nullptr, instance, nullptr);

  if (window == nullptr) {
    return EXIT_FAILURE;
  }

  // Set up Flutter
  SetParent(controller.GetNativeWindow(), window);
  
  // Message loop
  MSG msg;
  while (GetMessage(&msg, nullptr, 0, 0)) {
    TranslateMessage(&msg);
    DispatchMessage(&msg);
  }

  return EXIT_SUCCESS;
}
