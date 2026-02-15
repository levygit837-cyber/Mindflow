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
    <div className="py-1 animate-fade-in-up">
      <div
        className={cn(
          "prose prose-sm dark:prose-invert max-w-none",
          "prose-p:my-1.5 prose-headings:my-2 prose-pre:my-2",
          "prose-code:before:content-none prose-code:after:content-none",
          "prose-code:rounded-md prose-code:bg-zinc-800/60 prose-code:px-1.5 prose-code:py-0.5 prose-code:text-[13px] prose-code:font-mono prose-code:text-zinc-300",
          "prose-pre:rounded-lg prose-pre:bg-zinc-900/60 prose-pre:border prose-pre:border-zinc-800 prose-pre:text-zinc-300",
          "prose-a:text-zinc-400 prose-a:underline prose-a:decoration-zinc-700 hover:prose-a:text-zinc-300",
          "prose-table:text-xs prose-th:text-left",
          "prose-li:my-0.5",
          "prose-strong:text-zinc-200",
          "prose-headings:text-zinc-200",
          "text-zinc-300"
        )}
      >
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
          {content}
        </ReactMarkdown>
        {isStreaming && (
          <span
            className={cn(
              "ml-0.5 inline-block w-1 h-4 rounded-sm",
              "bg-zinc-400 animate-typewriter-blink"
            )}
          />
        )}
      </div>
    </div>
  );
}

export const ResponseBlock = React.memo(ResponseBlockInner);
