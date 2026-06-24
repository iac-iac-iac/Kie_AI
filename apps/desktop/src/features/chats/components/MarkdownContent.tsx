import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { codeToHtml } from "shiki";

interface MarkdownContentProps {
  content: string;
}

function CodeBlock({ code, lang }: { code: string; lang?: string }) {
  const [html, setHtml] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    codeToHtml(code, {
      lang: lang || "text",
      theme: "github-dark",
    })
      .then((result) => {
        if (!cancelled) setHtml(result);
      })
      .catch(() => {
        if (!cancelled) setHtml(`<pre><code>${code}</code></pre>`);
      });
    return () => {
      cancelled = true;
    };
  }, [code, lang]);

  if (!html) {
    return (
      <pre className="my-2 overflow-x-auto rounded-lg bg-black/30 p-3 text-sm">
        <code>{code}</code>
      </pre>
    );
  }

  return (
    <div
      className="my-2 overflow-x-auto rounded-lg text-sm [&_pre]:p-3"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

export function MarkdownContent({ content }: MarkdownContentProps) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        code({ className, children, ...props }) {
          const match = /language-(\w+)/.exec(className ?? "");
          const code = String(children).replace(/\n$/, "");
          if (match || code.includes("\n")) {
            return <CodeBlock code={code} lang={match?.[1]} />;
          }
          return (
            <code
              className="rounded bg-black/20 px-1 py-0.5 text-sm"
              {...props}
            >
              {children}
            </code>
          );
        },
        p({ children }) {
          return <p className="mb-2 last:mb-0">{children}</p>;
        },
        ul({ children }) {
          return <ul className="mb-2 list-disc pl-5">{children}</ul>;
        },
        ol({ children }) {
          return <ol className="mb-2 list-decimal pl-5">{children}</ol>;
        },
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
