export interface Note {
  id: string;
  title: string;
  emoji: string;
  tags: string[];
  starred: boolean;
  color: string | null;
  createdAt: string;
  updatedAt: string;
  wordCount: number;
  preview: string;
}

export interface NoteWithContent extends Note {
  content: BlockNoteDocument;
}

// BlockNote document is stored as JSON
export type BlockNoteDocument = Record<string, unknown>[];

export interface CreateNoteInput {
  title?: string;
  emoji?: string;
  tags?: string[];
  color?: string;
}

export interface UpdateNoteInput {
  title?: string;
  emoji?: string;
  tags?: string[];
  starred?: boolean;
  color?: string;
}

export interface NoteSearchParams {
  query?: string;
  tags?: string[];
  starred?: boolean;
  sortBy?: "updatedAt" | "createdAt" | "title";
  sortOrder?: "asc" | "desc";
  limit?: number;
  offset?: number;
}
