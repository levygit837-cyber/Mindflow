"use client";

import React, { useState } from "react";
import { Globe, ExternalLink, ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface SearchResult {
  title: string;
  url: string;
  snippet: string;
}

interface SearchResultBlockProps {
  results: SearchResult[];
  query?: string;
  isSearching?: boolean;
}

function extractDomain(url: string): string {
  try {
    const u = new URL(url);
    return u.hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function SearchResultBlockInner({ results, query, isSearching }: SearchResultBlockProps) {
  const [expanded, setExpanded] = useState(false);
  const displayResults = expanded ? results : results.slice(0, 3);

  return (
    <div className="mb-2 rounded-xl backdrop-blur-md bg-white/[0.02] border border-white/[0.08] animate-fade-in-up">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 text-xs">
        <Globe
          className={cn(
            "h-3.5 w-3.5 shrink-0 text-sky-400",
            isSearching && "animate-spin"
          )}
        />
        <span className="font-medium text-foreground/70">
          Web Search
          {query && (
            <span className="text-muted-foreground/40 ml-1.5 font-normal">
              &quot;{query}&quot;
            </span>
          )}
        </span>
        <span className="ml-auto text-[10px] text-muted-foreground/40">
          {results.length} results
        </span>
      </div>

      {/* Results */}
      <div className="border-t border-white/[0.06] px-3 py-2 space-y-2">
        {displayResults.map((result, i) => (
          <a
            key={i}
            href={result.url}
            target="_blank"
            rel="noopener noreferrer"
            className={cn(
              "block rounded-lg px-3 py-2 transition-colors",
              "hover:bg-white/[0.04] group"
            )}
          >
            <div className="flex items-start gap-2">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-medium text-cyan-400 group-hover:text-cyan-300 truncate">
                    {result.title}
                  </span>
                  <ExternalLink className="h-2.5 w-2.5 shrink-0 text-muted-foreground/30 group-hover:text-cyan-400/50" />
                </div>
                <div className="text-[10px] text-muted-foreground/30 mt-0.5 truncate">
                  {extractDomain(result.url)}
                </div>
                {result.snippet && (
                  <p className="text-[11px] text-muted-foreground/50 mt-1 line-clamp-2 leading-relaxed">
                    {result.snippet}
                  </p>
                )}
              </div>
            </div>
          </a>
        ))}
      </div>

      {/* Show more / less */}
      {results.length > 3 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex w-full items-center justify-center gap-1 border-t border-white/[0.06] px-3 py-1.5 text-[10px] text-muted-foreground/40 hover:text-muted-foreground/60 transition-colors"
        >
          {expanded ? (
            <>
              <ChevronDown className="h-3 w-3" />
              Show less
            </>
          ) : (
            <>
              <ChevronRight className="h-3 w-3" />
              Show {results.length - 3} more
            </>
          )}
        </button>
      )}
    </div>
  );
}

export const SearchResultBlock = React.memo(SearchResultBlockInner);
