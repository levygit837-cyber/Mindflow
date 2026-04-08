import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'core/theme/app_colors.dart';
import 'screens/chat_screen.dart';
import 'components/window_title_bar.dart';

class MindFlowApp extends StatelessWidget {
  const MindFlowApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MindFlow',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: AppColors.bgPrimary,
        primaryColor: AppColors.signalSynapse,
        colorScheme: const ColorScheme.dark(
          primary: AppColors.signalSynapse,
          secondary: AppColors.agentOrchestrator,
          surface: AppColors.bgSurface,
          background: AppColors.bgPrimary,
          onSurface: AppColors.textPrimary,
          onBackground: AppColors.textPrimary,
        ),
        textTheme: TextTheme(
          headlineLarge: GoogleFonts.inter(
            fontSize: 28,
            fontWeight: FontWeight.w600,
            color: AppColors.textPrimary,
          ),
          headlineMedium: GoogleFonts.inter(
            fontSize: 24,
            fontWeight: FontWeight.w600,
            color: AppColors.textPrimary,
          ),
          titleLarge: GoogleFonts.inter(
            fontSize: 20,
            fontWeight: FontWeight.w600,
            color: AppColors.textPrimary,
          ),
          titleMedium: GoogleFonts.inter(
            fontSize: 16,
            fontWeight: FontWeight.w500,
            color: AppColors.textPrimary,
          ),
          bodyLarge: GoogleFonts.inter(
            fontSize: 16,
            fontWeight: FontWeight.normal,
            color: AppColors.textSecondary,
          ),
          bodyMedium: GoogleFonts.inter(
            fontSize: 14,
            fontWeight: FontWeight.normal,
            color: AppColors.textSecondary,
          ),
          bodySmall: GoogleFonts.inter(
            fontSize: 12,
            fontWeight: FontWeight.normal,
            color: AppColors.textMeta,
          ),
          labelLarge: GoogleFonts.jetBrainsMono(
            fontSize: 13,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.3,
            color: AppColors.textPrimary,
          ),
          labelMedium: GoogleFonts.jetBrainsMono(
            fontSize: 11,
            fontWeight: FontWeight.w600,
            letterSpacing: 2,
            color: AppColors.textMeta,
          ),
          labelSmall: GoogleFonts.jetBrainsMono(
            fontSize: 10,
            fontWeight: FontWeight.w600,
            letterSpacing: 1.5,
            color: AppColors.textMeta,
          ),
        ),
        cardTheme: const CardThemeData(
          color: AppColors.bgSurface,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.all(Radius.circular(12)),
            side: BorderSide(color: AppColors.linePrimary),
          ),
        ),
      ),
      home: const WindowLayout(),
    );
  }
}

class WindowLayout extends StatelessWidget {
  const WindowLayout({super.key});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Custom title bar
        const WindowTitleBar(),
        // Main content
        Expanded(
          child: const ChatScreen(),
        ),
      ],
    );
  }
}
