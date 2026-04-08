import 'package:flutter/material.dart';
import 'package:flutter_lucide/flutter_lucide.dart';
import 'package:provider/provider.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';
import '../../core/services/websocket_service.dart';

/// Model selector button in input toolbar
/// 
/// From Pencil: iaTool2 (eRjO5)
/// - Text: model name (e.g., "claude-4-sonnet")
/// - Icon: Lucide chevron-down
/// - Height: 28px
/// - Padding: 0,10
/// - Border radius: 6px
class ModelSelector extends StatelessWidget {
  const ModelSelector({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<WebSocketService>(
      builder: (context, service, child) {
        return InkWell(
          onTap: () {
            _showModelDialog(context, service);
          },
          borderRadius: BorderRadius.circular(6),
          child: Container(
            height: 28,
            padding: const EdgeInsets.symmetric(horizontal: 10),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  service.selectedModel,
                  style: AppTypography.toolbarText,
                ),
                const SizedBox(width: 5),
                const Icon(
                  LucideIcons.chevron_down,
                  size: 13,
                  color: AppColors.textMeta,
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  void _showModelDialog(BuildContext context, WebSocketService service) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.bgSurface,
        title: Text(
          'Selecionar Modelo',
          style: AppTypography.userName,
        ),
        content: SizedBox(
          width: 300,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: service.availableModels.map((model) {
              final isSelected = model == service.selectedModel;
              return ListTile(
                title: Text(
                  model,
                  style: AppTypography.sessionTitle.copyWith(
                    color: isSelected
                        ? AppColors.textPrimary
                        : AppColors.textSecondary,
                  ),
                ),
                trailing: isSelected
                    ? const Icon(
                        LucideIcons.check,
                        size: 16,
                        color: AppColors.signalSynapse,
                      )
                    : null,
                onTap: () {
                  service.setSelectedModel(model);
                  Navigator.pop(context);
                },
              );
            }).toList(),
          ),
        ),
      ),
    );
  }
}
