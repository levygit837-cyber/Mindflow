"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { cn } from "@/lib/utils";

interface ResponseBlockProps {
  content: string;
  isStreaming: boolean;
}

function ResponseBlockInner({ content, isStreaming }: ResponseBlockProps) {
  if (!content && !isStreaming) return null;

  return (
    <div className="mb-2">
      <div
        className={cn(
          "prose prose-sm dark:prose-invert max-w-none",
          "prose-p:my-1.5 prose-headings:my-2 prose-pre:my-2",
          "prose-code:before:content-none prose-code:after:content-none",
          "prose-code:rounded prose-code:bg-muted/60 prose-code:px-1.5 prose-code:py-0.5 prose-code:text-[13px]",
          "prose-pre:rounded-lg prose-pre:bg-muted/40 prose-pre:border prose-pre:border-muted",
          "prose-a:text-blue-500 prose-a:no-underline hover:prose-a:underline",
          "prose-table:text-xs prose-th:text-left",
          "prose-li:my-0.5"
        )}
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
          {content}
        </ReactMarkdown>
        {isStreaming && (
          <span className="ml-0.5 inline-block w-1.5 h-4 bg-foreground/60 animate-blink rounded-sm" />
        )}
      </div>
    </div>
  );
}

export const ResponseBlock = React.memo(ResponseBlockInner);
