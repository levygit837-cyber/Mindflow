import React from 'react';
import ReactMarkdown from 'react-markdown';

interface RichTextProps {
  content: string;
  className?: string;
}

function normalizeCodeChildren(children: React.ReactNode): string {
  if (Array.isArray(children)) {
    return children.map((child) => String(child)).join('');
  }

  return String(children);
}

export const RichText: React.FC<RichTextProps> = ({ content, className = '' }) => {
  return (
    <div className={['rich-text', className].filter(Boolean).join(' ')}>
      <ReactMarkdown
        components={{
          pre({ children }) {
            return <>{children}</>;
          },
          h1({ children }) {
            return <h1 className="rich-text-heading rich-text-heading-1">{children}</h1>;
          },
          h2({ children }) {
            return <h2 className="rich-text-heading rich-text-heading-2">{children}</h2>;
          },
          h3({ children }) {
            return <h3 className="rich-text-heading rich-text-heading-3">{children}</h3>;
          },
          h4({ children }) {
            return <h4 className="rich-text-heading rich-text-heading-4">{children}</h4>;
          },
          blockquote({ children }) {
            return <blockquote className="rich-text-blockquote">{children}</blockquote>;
          },
          a({ href, children }) {
            return (
              <a
                className="rich-text-link"
                href={href}
                target="_blank"
                rel="noreferrer"
              >
                {children}
              </a>
            );
          },
          code({ className: codeClassName, children, ...props }) {
            const text = normalizeCodeChildren(children).replace(/\n$/, '');
            const isBlock = Boolean(codeClassName?.includes('language-')) || text.includes('\n');

            if (!isBlock) {
              return (
                <code className="rich-text-inline-code" {...props}>
                  {children}
                </code>
              );
            }

            return (
              <pre className="rich-text-code-block">
                <code className={codeClassName} {...props}>
                  {text}
                </code>
              </pre>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

export default RichText;
