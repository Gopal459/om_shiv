import React, { useRef, useEffect, useState } from 'react';
import {
  Bold,
  Italic,
  Underline,
  Strikethrough,
  Heading1,
  Heading2,
  Heading3,
  List,
  ListOrdered,
  Quote,
  AlignLeft,
  AlignCenter,
  AlignRight,
  Link as LinkIcon,
  Image as ImageIcon,
  Code,
  Undo,
  Redo,
  RemoveFormatting,
  Eye,
  Edit3,
  Minus,
  Upload,
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

interface RichTextEditorProps {
  value: string;
  onChange: (html: string) => void;
  placeholder?: string;
  minHeight?: string;
}

export const RichTextEditor: React.FC<RichTextEditorProps> = ({
  value,
  onChange,
  placeholder = 'Write full article content here...',
  minHeight = '360px',
}) => {
  const { isDark } = useTheme();
  const editorRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<'visual' | 'html' | 'preview'>('visual');
  const [htmlContent, setHtmlContent] = useState(value || '');
  const [isUploading, setIsUploading] = useState(false);

  // Sync internal editor with value on initial load or reset
  useEffect(() => {
    if (editorRef.current && mode === 'visual') {
      if (editorRef.current.innerHTML !== value) {
        editorRef.current.innerHTML = value || '';
      }
    }
    setHtmlContent(value || '');
  }, [value, mode]);

  const executeCommand = (command: string, arg: string | undefined = undefined) => {
    if (mode !== 'visual') return;
    document.execCommand(command, false, arg);
    if (editorRef.current) {
      const updated = editorRef.current.innerHTML;
      setHtmlContent(updated);
      onChange(updated);
    }
  };

  const handleInput = () => {
    if (editorRef.current) {
      const updated = editorRef.current.innerHTML;
      setHtmlContent(updated);
      onChange(updated);
    }
  };

  const handleHtmlCodeChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setHtmlContent(val);
    onChange(val);
  };

  const handleInsertLink = () => {
    const url = window.prompt('Enter link URL (e.g. https://propira.com):');
    if (url) {
      executeCommand('createLink', url);
    }
  };

  const handleInsertImageUrl = () => {
    const url = window.prompt('Enter image web URL:');
    if (url) {
      executeCommand('insertImage', url);
    }
  };

  const handleDirectImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const token = localStorage.getItem('access_token');
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/v1/blogs/upload-image', {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        if (data.url) {
          executeCommand('insertImage', data.url);
        }
      } else {
        alert('Image upload failed.');
      }
    } catch (err) {
      alert('Network error uploading image.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className={`rounded-xl border shadow-sm transition ${isDark ? 'border-slate-800 bg-slate-900' : 'border-slate-200 bg-white'}`}>
      {/* Hidden File Input for Image Upload */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleDirectImageUpload}
        accept="image/png, image/jpeg, image/webp"
        className="hidden"
      />

      {/* Editor Top Toolbar */}
      <div className={`p-2 border-b flex flex-wrap items-center justify-between gap-1.5 ${isDark ? 'border-slate-800 bg-slate-900/90' : 'border-slate-200 bg-slate-50'}`}>
        <div className="flex flex-wrap items-center gap-1">
          {/* Format Blocks */}
          <select
            onChange={(e) => executeCommand('formatBlock', e.target.value)}
            disabled={mode !== 'visual'}
            className={`px-2 py-1 text-xs rounded border outline-none cursor-pointer ${
              isDark ? 'bg-slate-800 border-slate-700 text-slate-200' : 'bg-white border-slate-300 text-slate-700'
            }`}
            defaultValue="p"
          >
            <option value="p">Paragraph</option>
            <option value="h1">Heading 1</option>
            <option value="h2">Heading 2</option>
            <option value="h3">Heading 3</option>
            <option value="blockquote">Quote Block</option>
            <option value="pre">Code Block</option>
          </select>

          <div className="h-4 w-px bg-slate-300 dark:bg-slate-700 mx-1" />

          {/* Inline Styles */}
          <button
            type="button"
            title="Bold (Ctrl+B)"
            onClick={() => executeCommand('bold')}
            disabled={mode !== 'visual'}
            className="p-1.5 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
          >
            <Bold className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            title="Italic (Ctrl+I)"
            onClick={() => executeCommand('italic')}
            disabled={mode !== 'visual'}
            className="p-1.5 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
          >
            <Italic className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            title="Underline (Ctrl+U)"
            onClick={() => executeCommand('underline')}
            disabled={mode !== 'visual'}
            className="p-1.5 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
          >
            <Underline className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            title="Strikethrough"
            onClick={() => executeCommand('strikeThrough')}
            disabled={mode !== 'visual'}
            className="p-1.5 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
          >
            <Strikethrough className="w-3.5 h-3.5" />
          </button>

          <div className="h-4 w-px bg-slate-300 dark:bg-slate-700 mx-1" />

          {/* Lists & Alignment */}
          <button
            type="button"
            title="Bullet List"
            onClick={() => executeCommand('insertUnorderedList')}
            disabled={mode !== 'visual'}
            className="p-1.5 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
          >
            <List className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            title="Numbered List"
            onClick={() => executeCommand('insertOrderedList')}
            disabled={mode !== 'visual'}
            className="p-1.5 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
          >
            <ListOrdered className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            title="Horizontal Divider"
            onClick={() => executeCommand('insertHorizontalRule')}
            disabled={mode !== 'visual'}
            className="p-1.5 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
          >
            <Minus className="w-3.5 h-3.5" />
          </button>

          <div className="h-4 w-px bg-slate-300 dark:bg-slate-700 mx-1" />

          <button
            type="button"
            title="Align Left"
            onClick={() => executeCommand('justifyLeft')}
            disabled={mode !== 'visual'}
            className="p-1.5 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
          >
            <AlignLeft className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            title="Align Center"
            onClick={() => executeCommand('justifyCenter')}
            disabled={mode !== 'visual'}
            className="p-1.5 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
          >
            <AlignCenter className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            title="Align Right"
            onClick={() => executeCommand('justifyRight')}
            disabled={mode !== 'visual'}
            className="p-1.5 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
          >
            <AlignRight className="w-3.5 h-3.5" />
          </button>

          <div className="h-4 w-px bg-slate-300 dark:bg-slate-700 mx-1" />

          {/* Links & Media */}
          <button
            type="button"
            title="Insert Hyperlink"
            onClick={handleInsertLink}
            disabled={mode !== 'visual'}
            className="p-1.5 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-rose-500 transition"
          >
            <LinkIcon className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            title="Insert Image by URL"
            onClick={handleInsertImageUrl}
            disabled={mode !== 'visual'}
            className="p-1.5 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-rose-500 transition"
          >
            <ImageIcon className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            title="Upload Image Into Article"
            onClick={() => fileInputRef.current?.click()}
            disabled={mode !== 'visual' || isUploading}
            className="flex items-center gap-1 px-2 py-1 text-xs rounded bg-rose-50 text-rose-600 hover:bg-rose-100 dark:bg-rose-950/60 dark:text-rose-400 font-medium transition"
          >
            <Upload className="w-3 h-3" />
            {isUploading ? 'Uploading...' : 'Insert Photo'}
          </button>

          <div className="h-4 w-px bg-slate-300 dark:bg-slate-700 mx-1" />

          <button
            type="button"
            title="Undo"
            onClick={() => executeCommand('undo')}
            disabled={mode !== 'visual'}
            className="p-1.5 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
          >
            <Undo className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            title="Redo"
            onClick={() => executeCommand('redo')}
            disabled={mode !== 'visual'}
            className="p-1.5 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
          >
            <Redo className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            title="Clear Formatting"
            onClick={() => executeCommand('removeFormat')}
            disabled={mode !== 'visual'}
            className="p-1.5 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 transition"
          >
            <RemoveFormatting className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* View Mode Switchers */}
        <div className="flex items-center gap-1 border-l pl-2 border-slate-200 dark:border-slate-800">
          <button
            type="button"
            onClick={() => setMode('visual')}
            className={`flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded transition ${
              mode === 'visual'
                ? 'bg-rose-600 text-white shadow-sm'
                : 'text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-800'
            }`}
          >
            <Edit3 className="w-3 h-3" /> Visual Editor
          </button>
          <button
            type="button"
            onClick={() => setMode('html')}
            className={`flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded transition ${
              mode === 'html'
                ? 'bg-rose-600 text-white shadow-sm'
                : 'text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-800'
            }`}
          >
            <Code className="w-3 h-3" /> HTML Code
          </button>
          <button
            type="button"
            onClick={() => setMode('preview')}
            className={`flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded transition ${
              mode === 'preview'
                ? 'bg-rose-600 text-white shadow-sm'
                : 'text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-800'
            }`}
          >
            <Eye className="w-3 h-3" /> Reader Preview
          </button>
        </div>
      </div>

      {/* Editor Body Area */}
      <div className="relative">
        {mode === 'visual' && (
          <div
            ref={editorRef}
            contentEditable
            onInput={handleInput}
            style={{ minHeight }}
            data-placeholder={placeholder}
            className={`p-5 outline-none leading-relaxed overflow-y-auto text-sm ${
              isDark ? 'text-slate-100 bg-slate-900' : 'text-slate-800 bg-white'
            } [&_h1]:text-2xl [&_h1]:font-bold [&_h1]:my-3 [&_h2]:text-xl [&_h2]:font-bold [&_h2]:my-2.5 [&_h3]:text-lg [&_h3]:font-semibold [&_h3]:my-2 [&_p]:my-2 [&_ul]:list-disc [&_ul]:ml-6 [&_ol]:list-decimal [&_ol]:ml-6 [&_blockquote]:border-l-4 [&_blockquote]:border-rose-500 [&_blockquote]:pl-4 [&_blockquote]:italic [&_blockquote]:my-3 [&_img]:rounded-xl [&_img]:max-w-full [&_img]:my-3 [&_hr]:my-4 [&_hr]:border-slate-200 dark:[&_hr]:border-slate-800`}
          />
        )}

        {mode === 'html' && (
          <textarea
            value={htmlContent}
            onChange={handleHtmlCodeChange}
            style={{ minHeight }}
            placeholder="Edit raw HTML code..."
            className={`w-full p-5 font-mono text-xs outline-none resize-y ${
              isDark ? 'bg-slate-950 text-emerald-400' : 'bg-slate-900 text-emerald-400'
            }`}
          />
        )}

        {mode === 'preview' && (
          <div
            style={{ minHeight }}
            className={`p-6 overflow-y-auto ${isDark ? 'bg-slate-950 text-slate-100' : 'bg-slate-50 text-slate-800'}`}
          >
            <div
              className={`prose max-w-none text-sm leading-relaxed ${
                isDark ? 'prose-invert text-slate-200' : 'text-slate-800'
              } [&_h1]:text-2xl [&_h1]:font-bold [&_h1]:my-3 [&_h2]:text-xl [&_h2]:font-bold [&_h2]:my-2.5 [&_h3]:text-lg [&_h3]:font-semibold [&_h3]:my-2 [&_p]:my-2 [&_ul]:list-disc [&_ul]:ml-6 [&_ol]:list-decimal [&_ol]:ml-6 [&_blockquote]:border-l-4 [&_blockquote]:border-rose-500 [&_blockquote]:pl-4 [&_blockquote]:italic [&_blockquote]:my-3 [&_img]:rounded-xl [&_img]:max-w-full [&_img]:my-3 [&_hr]:my-4 [&_hr]:border-slate-200 dark:[&_hr]:border-slate-800`}
              dangerouslySetInnerHTML={{ __html: htmlContent || '<p className="text-slate-400 italic">No content written yet.</p>' }}
            />
          </div>
        )}
      </div>

      {/* Editor Footer Status */}
      <div className={`px-4 py-2 border-t text-[11px] flex items-center justify-between ${
        isDark ? 'border-slate-800 bg-slate-900/60 text-slate-400' : 'border-slate-200 bg-slate-50 text-slate-500'
      }`}>
        <span>Rich Text WYSIWYG Editor (HTML supported)</span>
        <span>Word count: {htmlContent.replace(/<[^>]+>/g, '').trim().split(/\s+/).filter(Boolean).length} words</span>
      </div>
    </div>
  );
};

export default RichTextEditor;
