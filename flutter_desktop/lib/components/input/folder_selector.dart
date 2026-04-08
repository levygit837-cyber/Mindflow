import 'package:flutter/material.dart';
import 'package:flutter_lucide/flutter_lucide.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_typography.dart';

/// Folder selector button in input toolbar
/// 
/// From Pencil: iaTool1 (uXk55)
/// - Icon: Lucide paperclip
/// - Text: "folder"
/// - Height: 28px
/// - Padding: 0,10
/// - Border radius: 6px
class FolderSelector extends StatelessWidget {
  const FolderSelector({super.key});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () {
        // Show folder selection dialog
        _showFolderDialog(context);
      },
      borderRadius: BorderRadius.circular(6),
      child: Container(
        height: 28,
        padding: const EdgeInsets.symmetric(horizontal: 10),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              LucideIcons.paperclip,
              size: 13,
              color: AppColors.textMeta,
            ),
            const SizedBox(width: 5),
            Text(
              'folder',
              style: AppTypography.toolbarText,
            ),
          ],
        ),
      ),
    );
  }

  void _showFolderDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.bgSurface,
        title: Text(
          'Selecionar Pasta',
          style: AppTypography.userName,
        ),
        content: SizedBox(
          width: 400,
          height: 300,
          child: ListView(
            children: [
              _FolderItem(name: 'workspace/project-a', isSelected: true),
              _FolderItem(name: 'workspace/project-b', isSelected: false),
              _FolderItem(name: 'documents/research', isSelected: false),
              _FolderItem(name: 'code/backend', isSelected: false),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text(
              'Cancelar',
              style: AppTypography.toolbarText.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _FolderItem extends StatelessWidget {
  final String name;
  final bool isSelected;

  const _FolderItem({
    required this.name,
    required this.isSelected,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(
        LucideIcons.folder,
        size: 16,
        color: isSelected ? AppColors.signalSynapse : AppColors.textMeta,
      ),
      title: Text(
        name,
        style: AppTypography.sessionTitle.copyWith(
          color: isSelected ? AppColors.textPrimary : AppColors.textSecondary,
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
        Navigator.pop(context, name);
      },
    );
  }
}
