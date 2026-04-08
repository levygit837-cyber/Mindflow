import 'package:flutter/material.dart';
import 'package:flutter_lucide/flutter_lucide.dart';
import 'package:window_manager/window_manager.dart';
import '../core/theme/app_colors.dart';
import '../core/theme/app_typography.dart';

/// Custom title bar for MindFlow Desktop
/// Provides a custom window frame with minimize, maximize, and close buttons
class WindowTitleBar extends StatelessWidget {
  const WindowTitleBar({super.key});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onPanStart: (details) {
        windowManager.startDragging();
      },
      child: Container(
        color: AppColors.bgPrimary,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: Row(
            children: [
              // Logo/Icon
              Container(
                width: 24,
                height: 24,
                decoration: BoxDecoration(
                  color: AppColors.signalSynapse,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: const Icon(
                  LucideIcons.sparkles,
                  size: 14,
                  color: Colors.white,
                ),
              ),
              const SizedBox(width: 12),
              // Title
              Text(
                'MindFlow',
                style: AppTypography.logoText.copyWith(
                  color: AppColors.textPrimary,
                ),
              ),
              const Spacer(),
              // Window controls
              Row(
                children: [
                  _WindowButton(
                    icon: LucideIcons.minus,
                    onPressed: () async {
                      await windowManager.minimize();
                    },
                  ),
                  const SizedBox(width: 8),
                  _WindowButton(
                    icon: LucideIcons.square,
                    onPressed: () async {
                      final isMaximized = await windowManager.isMaximized();
                      if (isMaximized) {
                        await windowManager.unmaximize();
                      } else {
                        await windowManager.maximize();
                      }
                    },
                  ),
                  const SizedBox(width: 8),
                  _WindowButton(
                    icon: LucideIcons.x,
                    isCloseButton: true,
                    onPressed: () async {
                      await windowManager.close();
                    },
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _WindowButton extends StatefulWidget {
  final IconData icon;
  final bool isCloseButton;
  final VoidCallback onPressed;

  const _WindowButton({
    required this.icon,
    this.isCloseButton = false,
    required this.onPressed,
  });

  @override
  State<_WindowButton> createState() => _WindowButtonState();
}

class _WindowButtonState extends State<_WindowButton> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: GestureDetector(
        onTap: widget.onPressed,
        child: Container(
          width: 32,
          height: 32,
          decoration: BoxDecoration(
            color: _isHovered
                ? (widget.isCloseButton ? const Color(0xFFE81123) : AppColors.bgSurface)
                : Colors.transparent,
            borderRadius: BorderRadius.circular(6),
          ),
          child: Icon(
            widget.icon,
            size: 16,
            color: _isHovered
                ? (widget.isCloseButton ? Colors.white : AppColors.textPrimary)
                : AppColors.textSecondary,
          ),
        ),
      ),
    );
  }
}
