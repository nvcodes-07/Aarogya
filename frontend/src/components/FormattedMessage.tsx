import React from 'react';

interface FormattedMessageProps {
  content: string;
  isUser?: boolean;
}

export const FormattedMessage: React.FC<FormattedMessageProps> = ({ content, isUser = false }) => {
  if (isUser) {
    return <div className="whitespace-pre-wrap">{content}</div>;
  }

  // Parse inline text: bold (***bold italic***, **bold**, __bold__), italic (*italic*, _italic_), code (`code`), and plain text
  const renderInline = (text: string): React.ReactNode[] => {
    // Regex splits by bold italic (***), bold (**, __), italic (*, _), or code (`)
    const tokenRegex = /(\*\*\*[^*]+?\*\*\*|\*\*[^*]+?\*\*|__[^_]+?__|(?<!\*)\*[^*]+?\*(?!\*)|(?<!_)_[^_]+?_(?!_)|`[^`]+?`)/g;
    const parts = text.split(tokenRegex);

    return parts.map((part, idx) => {
      if (!part) return null;

      // Bold + Italic: ***text***
      if (part.startsWith('***') && part.endsWith('***') && part.length > 6) {
        return (
          <strong key={idx} className="font-bold text-slate-900">
            <em className="italic">{part.slice(3, -3)}</em>
          </strong>
        );
      }

      // Bold: **text** or __text__
      if (
        ((part.startsWith('**') && part.endsWith('**')) || (part.startsWith('__') && part.endsWith('__'))) &&
        part.length > 4
      ) {
        return (
          <strong key={idx} className="font-bold text-slate-900">
            {part.slice(2, -2)}
          </strong>
        );
      }

      // Italic: *text* or _text_
      if (
        ((part.startsWith('*') && part.endsWith('*')) || (part.startsWith('_') && part.endsWith('_'))) &&
        part.length > 2
      ) {
        return (
          <em key={idx} className="italic text-slate-700">
            {part.slice(1, -1)}
          </em>
        );
      }

      // Inline code: `text`
      if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
        return (
          <code
            key={idx}
            className="px-1.5 py-0.5 mx-0.5 rounded bg-teal-50 text-teal-800 font-mono text-xs border border-teal-200 font-semibold"
          >
            {part.slice(1, -1)}
          </code>
        );
      }

      // Strip any stray or unmatched formatting markers if needed, or return clean text
      return <span key={idx}>{part}</span>;
    });
  };

  // Split into paragraphs / lines
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let currentListItems: React.ReactNode[] = [];

  const flushList = () => {
    if (currentListItems.length > 0) {
      elements.push(
        <ul key={`list-${elements.length}`} className="my-2 space-y-1 pl-1">
          {currentListItems}
        </ul>
      );
      currentListItems = [];
    }
  };

  lines.forEach((line, index) => {
    const trimmed = line.trim();

    // Empty line -> break/spacing
    if (!trimmed) {
      flushList();
      elements.push(<div key={`space-${index}`} className="h-2" />);
      return;
    }

    // Bullet items (• or - or *)
    if (trimmed.startsWith('• ') || trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      const itemText = trimmed.replace(/^[•\-\*]\s+/, '');
      currentListItems.push(
        <li key={`item-${index}`} className="flex items-start space-x-2 text-slate-800 text-sm">
          <span className="text-teal-600 font-bold select-none leading-relaxed">•</span>
          <span className="flex-1 leading-relaxed">{renderInline(itemText)}</span>
        </li>
      );
      return;
    }

    // Numbered list items (e.g. "1. ")
    const numMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);
    if (numMatch) {
      flushList();
      elements.push(
        <div key={`num-${index}`} className="flex items-start space-x-2 my-1 text-slate-800 text-sm">
          <span className="font-bold text-teal-700 min-w-[1.2rem]">{numMatch[1]}.</span>
          <span className="flex-1 leading-relaxed">{renderInline(numMatch[2])}</span>
        </div>
      );
      return;
    }

    // Normal line / paragraph
    flushList();

    // Check for Heading lines (### or ##)
    if (trimmed.startsWith('### ')) {
      elements.push(
        <h4 key={`h4-${index}`} className="font-bold text-slate-900 text-sm mt-3 mb-1">
          {renderInline(trimmed.replace(/^###\s+/, ''))}
        </h4>
      );
    } else if (trimmed.startsWith('## ')) {
      elements.push(
        <h3 key={`h3-${index}`} className="font-bold text-slate-900 text-base mt-3 mb-1">
          {renderInline(trimmed.replace(/^##\s+/, ''))}
        </h3>
      );
    } else if (trimmed.startsWith('🚨')) {
      // Critical emergency highlight line
      elements.push(
        <div
          key={`emergency-${index}`}
          className="p-3 my-2 rounded-xl bg-rose-50 border border-rose-300 text-rose-900 font-medium text-sm shadow-sm"
        >
          {renderInline(trimmed)}
        </div>
      );
    } else if (trimmed.startsWith('⚠️')) {
      // Warning highlight line
      elements.push(
        <div
          key={`warn-${index}`}
          className="p-3 my-2 rounded-xl bg-amber-50 border border-amber-300 text-amber-900 text-xs shadow-sm"
        >
          {renderInline(trimmed)}
        </div>
      );
    } else {
      elements.push(
        <p key={`p-${index}`} className="my-1 text-slate-800 text-sm leading-relaxed">
          {renderInline(trimmed)}
        </p>
      );
    }
  });

  flushList();

  return <div className="space-y-0.5">{elements}</div>;
};
