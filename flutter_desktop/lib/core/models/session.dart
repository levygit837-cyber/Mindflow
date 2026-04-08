import 'package:intl/intl.dart';

/// Represents a chat session in the sidebar
/// Matches Pencil design: session list with title and time
class Session {
  final String id;
  final String title;
  final DateTime lastActive;
  final bool isActive;
  
  const Session({
    required this.id,
    required this.title,
    required this.lastActive,
    this.isActive = false,
  });
  
  /// Format time as "2m", "1h", "3d" like in Pencil design
  String get timeAgo {
    final now = DateTime.now();
    final diff = now.difference(lastActive);
    
    if (diff.inMinutes < 1) {
      return 'agora';
    } else if (diff.inMinutes < 60) {
      return '${diff.inMinutes}m';
    } else if (diff.inHours < 24) {
      return '${diff.inHours}h';
    } else if (diff.inDays < 30) {
      return '${diff.inDays}d';
    } else {
      return DateFormat('dd/MM').format(lastActive);
    }
  }
  
  Session copyWith({
    String? id,
    String? title,
    DateTime? lastActive,
    bool? isActive,
  }) {
    return Session(
      id: id ?? this.id,
      title: title ?? this.title,
      lastActive: lastActive ?? this.lastActive,
      isActive: isActive ?? this.isActive,
    );
  }
  
  @override
  String toString() => 'Session(id: $id, title: $title, isActive: $isActive)';
  
  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is Session && other.id == id;
  }
  
  @override
  int get hashCode => id.hashCode;
}
