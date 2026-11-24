import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  BookOpen,
  Plus,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  Eye,
  Edit3,
  Trash2,
  Star,
  Home,
  MessageSquare,
  Tag,
  FolderPlus,
  UserPlus,
  UploadCloud,
  Globe,
  Share2,
  ChevronRight,
  ExternalLink,
  CornerDownRight,
  Send,
  AlertCircle,
  X,
  Check,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import RichTextEditor from '../components/RichTextEditor';

interface BlogCategory {
  blog_category_id: number;
  name: string;
  slug: string;
  meta_title?: string;
  meta_keyword?: string;
  meta_description?: string;
  status: number;
}

interface BlogTag {
  blog_tag_id: number;
  name: string;
  slug: string;
  status: number;
}

interface BlogAuthor {
  author_id: number;
  author_name: string;
  description: string;
  image: string;
  status: number;
}

interface BlogComment {
  blog_comm_id: number;
  blog_id: number;
  comment_id: number;
  name: string;
  email: string;
  comment: string;
  total_like: number;
  status: number;
  comment_by: string;
  created_date: string;
  replies?: BlogComment[];
}

interface BlogItem {
  blog_id: number;
  blog_category: string;
  category_ids: number[];
  category_names: string[];
  blog_title: string;
  blog_title_hindi?: string;
  slug: string;
  author_name: number;
  author_details?: BlogAuthor;
  blog_date: string;
  short_description: string;
  description: string;
  description_hindi?: string;
  tags_id: string;
  tag_ids: number[];
  tag_names: string[];
  image: string;
  meta_title: string;
  meta_keyword: string;
  meta_description: string;
  status: number;
  feature: number;
  homepage_status: number;
  total_view: number;
  created_date: string;
}

export const BlogManager: React.FC = () => {
  const { isDark } = useTheme();
  const token = localStorage.getItem('access_token');
  const authHeaders = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  // Active Main Tab
  const [activeTab, setActiveTab] = useState<'articles' | 'editor' | 'categories' | 'authors' | 'comments'>('articles');

  // Master Data
  const [categories, setCategories] = useState<BlogCategory[]>([]);
  const [tags, setTags] = useState<BlogTag[]>([]);
  const [authors, setAuthors] = useState<BlogAuthor[]>([]);

  // Articles List State
  const [articles, setArticles] = useState<BlogItem[]>([]);
  const [totalArticles, setTotalArticles] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState<string>('all');
  const [selectedStatusFilter, setSelectedStatusFilter] = useState<string>('all');
  const [isLoadingArticles, setIsLoadingArticles] = useState(false);

  // Editor Form State
  const [editingBlogId, setEditingBlogId] = useState<number | null>(null);
  const [titleEn, setTitleEn] = useState('');
  const [slug, setSlug] = useState('');
  const [autoSlug, setAutoSlug] = useState(true);
  const [authorId, setAuthorId] = useState<number>(0);
  const [selectedCatIds, setSelectedCatIds] = useState<number[]>([]);
  const [selectedTagIds, setSelectedTagIds] = useState<number[]>([]);
  const [shortDesc, setShortDesc] = useState('');
  const [bodyEn, setBodyEn] = useState('');
  const [featuredImage, setFeaturedImage] = useState('');
  const [metaTitle, setMetaTitle] = useState('');
  const [metaKeyword, setMetaKeyword] = useState('');
  const [metaDescription, setMetaDescription] = useState('');
  const [articleStatus, setArticleStatus] = useState<number>(1);
  const [articleFeature, setArticleFeature] = useState<number>(0);
  const [articleHomepage, setArticleHomepage] = useState<number>(0);
  const [isSavingArticle, setIsSavingArticle] = useState(false);
  const [isUploadingImage, setIsUploadingImage] = useState(false);
  const [editorTab, setEditorTab] = useState<'content' | 'seo'>('content');

  // Comments State
  const [comments, setComments] = useState<BlogComment[]>([]);
  const [commentFilter, setCommentFilter] = useState<number>(0); // 0=pending, 1=approved
  const [isLoadingComments, setIsLoadingComments] = useState(false);
  const [replyingToComment, setReplyingToComment] = useState<BlogComment | null>(null);
  const [adminReplyText, setAdminReplyText] = useState('');
  const [isSendingReply, setIsSendingReply] = useState(false);

  // Modals & New Meta Forms
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [newCatName, setNewCatName] = useState('');
  const [newCatSlug, setNewCatSlug] = useState('');
  const [newCatMetaTitle, setNewCatMetaTitle] = useState('');
  const [newCatMetaDesc, setNewCatMetaDesc] = useState('');

  const [newTagName, setNewTagName] = useState('');

  const [showAuthorModal, setShowAuthorModal] = useState(false);
  const [newAuthorName, setNewAuthorName] = useState('');
  const [newAuthorDesc, setNewAuthorDesc] = useState('');
  const [newAuthorImage, setNewAuthorImage] = useState('');

  // Toast / Status Message
  const [toastMessage, setToastMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const showToast = (text: string, type: 'success' | 'error' = 'success') => {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 4000);
  };

  // 1. Fetch Masters
  const fetchMasters = useCallback(async () => {
    try {
      const [catRes, tagRes, authorRes] = await Promise.all([
        fetch('/v1/blogs/meta/categories'),
        fetch('/v1/blogs/meta/tags'),
        fetch('/v1/blogs/meta/authors'),
      ]);
      if (catRes.ok) setCategories(await catRes.json());
      if (tagRes.ok) setTags(await tagRes.json());
      if (authorRes.ok) {
        const authData = await authorRes.json();
        setAuthors(authData);
        if (authData.length > 0 && authorId === 0) {
          setAuthorId(authData[0].author_id);
        }
      }
    } catch (err) {
      console.error('Failed to load blog masters', err);
    }
  }, [authorId]);

  // 2. Fetch Articles
  const fetchArticles = useCallback(async () => {
    setIsLoadingArticles(true);
    try {
      const params = new URLSearchParams();
      params.set('page', page.toString());
      params.set('limit', '15');
      if (search.trim()) params.set('search', search.trim());
      if (selectedCategoryFilter !== 'all') params.set('category_id', selectedCategoryFilter);
      if (selectedStatusFilter !== 'all') params.set('status', selectedStatusFilter);

      const res = await fetch(`/v1/blogs?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setArticles(data.items || []);
        setTotalArticles(data.total || 0);
      }
    } catch (err) {
      console.error('Error fetching blogs:', err);
    } finally {
      setIsLoadingArticles(false);
    }
  }, [page, search, selectedCategoryFilter, selectedStatusFilter]);

  // 3. Fetch Comments for Moderation
  const fetchComments = useCallback(async () => {
    setIsLoadingComments(true);
    try {
      const res = await fetch(`/v1/blogs/comments/moderation?status=${commentFilter}&limit=50`);
      if (res.ok) {
        const data = await res.json();
        setComments(data.items || []);
      }
    } catch (err) {
      console.error('Error loading comments:', err);
    } finally {
      setIsLoadingComments(false);
    }
  }, [commentFilter]);

  useEffect(() => {
    fetchMasters();
  }, [fetchMasters]);

  useEffect(() => {
    fetchArticles();
  }, [fetchArticles]);

  useEffect(() => {
    if (activeTab === 'comments') {
      fetchComments();
    }
  }, [activeTab, fetchComments]);

  // Handle Slug Autogeneration
  const handleTitleChange = (val: string) => {
    setTitleEn(val);
    if (autoSlug) {
      const s = val
        .toLowerCase()
        .replace(/[^\w\s-]/g, '')
        .replace(/[\s_-]+/g, '-')
        .replace(/^-+|-+$/g, '');
      setSlug(s);
    }
  };

  // Image Upload Handler
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploadingImage(true);
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
        setFeaturedImage(data.url);
        showToast('Image uploaded successfully!');
      } else {
        const err = await res.json();
        showToast(err.detail || 'Image upload failed', 'error');
      }
    } catch (err) {
      showToast('Network error uploading image', 'error');
    } finally {
      setIsUploadingImage(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // 1-Click Toggle for Article Card / Table
  const handleToggle = async (blogId: number, field: 'status' | 'feature' | 'homepage_status', currentVal: number) => {
    const newVal = currentVal === 1 ? 0 : 1;
    try {
      const res = await fetch(`/v1/blogs/${blogId}/toggle`, {
        method: 'PATCH',
        headers: authHeaders,
        body: JSON.stringify({ field, value: newVal }),
      });
      if (res.ok) {
        setArticles((prev) =>
          prev.map((b) => (b.blog_id === blogId ? { ...b, [field]: newVal } : b))
        );
        showToast(`Updated ${field} successfully`);
      }
    } catch (err) {
      showToast('Failed to update field', 'error');
    }
  };

  // Delete Article
  const handleDeleteArticle = async (blogId: number) => {
    if (!window.confirm('Are you sure you want to delete this blog article and its comments?')) return;
    try {
      const res = await fetch(`/v1/blogs/${blogId}`, {
        method: 'DELETE',
        headers: authHeaders,
      });
      if (res.ok) {
        showToast('Blog article deleted');
        fetchArticles();
      } else {
        showToast('Failed to delete blog', 'error');
      }
    } catch (err) {
      showToast('Error deleting blog', 'error');
    }
  };

  // Edit Article Pre-population
  const handleStartEdit = (b: BlogItem) => {
    setEditingBlogId(b.blog_id);
    setTitleEn(b.blog_title);
    setSlug(b.slug);
    setAutoSlug(false);
    setAuthorId(b.author_name);
    setSelectedCatIds(b.category_ids || []);
    setSelectedTagIds(b.tag_ids || []);
    setShortDesc(b.short_description);
    setBodyEn(b.description);
    setFeaturedImage(b.image || '');
    setMetaTitle(b.meta_title);
    setMetaKeyword(b.meta_keyword);
    setMetaDescription(b.meta_description);
    setArticleStatus(b.status);
    setArticleFeature(b.feature);
    setArticleHomepage(b.homepage_status);
    setActiveTab('editor');
  };

  // Reset Editor
  const handleResetEditor = () => {
    setEditingBlogId(null);
    setTitleEn('');
    setSlug('');
    setAutoSlug(true);
    setSelectedCatIds([]);
    setSelectedTagIds([]);
    setShortDesc('');
    setBodyEn('');
    setFeaturedImage('');
    setMetaTitle('');
    setMetaKeyword('');
    setMetaDescription('');
    setArticleStatus(1);
    setArticleFeature(0);
    setArticleHomepage(0);
  };

  // Save / Submit Article
  const handleSaveArticle = async () => {
    if (!titleEn.trim()) return showToast('Article Title is required', 'error');
    if (selectedCatIds.length === 0) return showToast('Select at least one category', 'error');
    if (selectedTagIds.length === 0) return showToast('Select at least one tag', 'error');
    if (!shortDesc.trim()) return showToast('Short excerpt is required', 'error');
    if (!bodyEn.trim()) return showToast('Full article content is required', 'error');

    setIsSavingArticle(true);
    const payload = {
      blog_title: titleEn.trim(),
      blog_title_hindi: null,
      slug: slug.trim(),
      author_name: authorId || (authors[0]?.author_id ?? 1),
      category_ids: selectedCatIds,
      tag_ids: selectedTagIds,
      short_description: shortDesc.trim(),
      description: bodyEn.trim(),
      description_hindi: null,
      image: featuredImage.trim(),
      meta_title: metaTitle.trim() || titleEn.trim(),
      meta_keyword: metaKeyword.trim(),
      meta_description: metaDescription.trim() || shortDesc.trim(),
      status: articleStatus,
      feature: articleFeature,
      homepage_status: articleHomepage,
    };

    try {
      const url = editingBlogId ? `/v1/blogs/${editingBlogId}` : '/v1/blogs';
      const method = editingBlogId ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
        headers: authHeaders,
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        showToast(editingBlogId ? 'Article updated successfully!' : 'Article published successfully!');
        handleResetEditor();
        setActiveTab('articles');
        fetchArticles();
      } else {
        const err = await res.json();
        showToast(err.detail || 'Failed to save article', 'error');
      }
    } catch (err) {
      showToast('Network error saving article', 'error');
    } finally {
      setIsSavingArticle(false);
    }
  };

  // Moderate Comment (Approve / Reject)
  const handleModerateComment = async (commId: number, newStatus: number) => {
    try {
      const res = await fetch(`/v1/blogs/comments/${commId}/status`, {
        method: 'PATCH',
        headers: authHeaders,
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) {
        showToast(newStatus === 1 ? 'Comment approved & live!' : 'Comment rejected');
        fetchComments();
      }
    } catch (err) {
      showToast('Error updating comment', 'error');
    }
  };

  // Delete Comment
  const handleDeleteComment = async (commId: number) => {
    if (!window.confirm('Delete this comment and its replies?')) return;
    try {
      const res = await fetch(`/v1/blogs/comments/${commId}`, {
        method: 'DELETE',
        headers: authHeaders,
      });
      if (res.ok) {
        showToast('Comment deleted');
        fetchComments();
      }
    } catch (err) {
      showToast('Error deleting comment', 'error');
    }
  };

  // Send Admin Threaded Reply
  const handleSendAdminReply = async () => {
    if (!replyingToComment || !adminReplyText.trim()) return;
    setIsSendingReply(true);
    try {
      const res = await fetch(`/v1/blogs/${replyingToComment.blog_id}/comments`, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          name: 'Propira Admin Desk',
          email: 'editorial@propira.com',
          comment: adminReplyText.trim(),
          comment_id: replyingToComment.blog_comm_id,
          comment_by: 'admin',
        }),
      });
      if (res.ok) {
        showToast('Official admin reply posted!');
        setReplyingToComment(null);
        setAdminReplyText('');
        fetchComments();
      } else {
        showToast('Failed to post reply', 'error');
      }
    } catch (err) {
      showToast('Error posting reply', 'error');
    } finally {
      setIsSendingReply(false);
    }
  };

  // Quick Add Category
  const handleCreateCategory = async () => {
    if (!newCatName.trim()) return;
    try {
      const res = await fetch('/v1/blogs/meta/categories', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          name: newCatName.trim(),
          slug: newCatSlug.trim() || undefined,
          meta_title: newCatMetaTitle.trim() || undefined,
          meta_description: newCatMetaDesc.trim() || undefined,
          status: 1,
        }),
      });
      if (res.ok) {
        showToast('Category created');
        setShowCategoryModal(false);
        setNewCatName('');
        setNewCatSlug('');
        setNewCatMetaTitle('');
        setNewCatMetaDesc('');
        fetchMasters();
      }
    } catch (err) {
      showToast('Error creating category', 'error');
    }
  };

  // Quick Add Tag
  const handleCreateTag = async () => {
    if (!newTagName.trim()) return;
    try {
      const res = await fetch('/v1/blogs/meta/tags', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ name: newTagName.trim(), status: 1 }),
      });
      if (res.ok) {
        showToast('Tag created');
        setNewTagName('');
        fetchMasters();
      }
    } catch (err) {
      showToast('Error creating tag', 'error');
    }
  };

  // Quick Add Author
  const handleCreateAuthor = async () => {
    if (!newAuthorName.trim() || !newAuthorDesc.trim()) {
      return showToast('Author name and description are required', 'error');
    }
    try {
      const res = await fetch('/v1/blogs/meta/authors', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({
          author_name: newAuthorName.trim(),
          description: newAuthorDesc.trim(),
          image: newAuthorImage.trim(),
          status: 1,
        }),
      });
      if (res.ok) {
        showToast('Author added');
        setShowAuthorModal(false);
        setNewAuthorName('');
        setNewAuthorDesc('');
        setNewAuthorImage('');
        fetchMasters();
      }
    } catch (err) {
      showToast('Error creating author', 'error');
    }
  };

  return (
    <div className={`min-h-screen p-6 transition-colors duration-200 ${isDark ? 'bg-slate-950 text-slate-100' : 'bg-slate-50 text-slate-800'}`}>
      {/* Toast Alert */}
      {toastMessage && (
        <div
          className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-5 py-3 rounded-xl shadow-2xl transition-all duration-300 animate-slide-in ${
            toastMessage.type === 'success'
              ? 'bg-emerald-600 text-white'
              : 'bg-rose-600 text-white'
          }`}
        >
          {toastMessage.type === 'success' ? <CheckCircle2 className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
          <span className="text-sm font-medium">{toastMessage.text}</span>
          <button onClick={() => setToastMessage(null)} className="ml-2 hover:opacity-75">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Header Banner */}
      <div className={`p-6 rounded-2xl border shadow-sm mb-6 ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-600 dark:bg-rose-950/60 dark:text-rose-400">
                Editorial & Media CMS
              </span>
              <span className="text-xs text-slate-400">100% Dynamic Content Engine</span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight mt-1 flex items-center gap-2">
              <BookOpen className="w-7 h-7 text-rose-500" />
              Blog & Real Estate Market Insights
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
              Publish investment outlooks, locality reports, and NCR real estate news with rich text formatting & SEO metadata.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => {
                handleResetEditor();
                setActiveTab('editor');
              }}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-rose-500 to-rose-600 text-white font-medium text-sm shadow-md hover:shadow-rose-500/25 hover:from-rose-600 hover:to-rose-700 transition"
            >
              <Plus className="w-4 h-4" />
              Write New Article
            </button>
          </div>
        </div>

        {/* Executive KPI Stats Bar */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-6 pt-6 border-t border-slate-100 dark:border-slate-800">
          <div className={`p-4 rounded-xl border ${isDark ? 'bg-slate-800/40 border-slate-800' : 'bg-slate-50/70 border-slate-200'}`}>
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Total Articles</span>
            <div className="text-2xl font-bold mt-1 text-slate-800 dark:text-white">{totalArticles}</div>
            <span className="text-xs text-emerald-500 font-medium">Dynamic database</span>
          </div>
          <div className={`p-4 rounded-xl border ${isDark ? 'bg-slate-800/40 border-slate-800' : 'bg-slate-50/70 border-slate-200'}`}>
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Active Published</span>
            <div className="text-2xl font-bold mt-1 text-emerald-600 dark:text-emerald-400">
              {articles.filter((a) => a.status === 1).length}
            </div>
            <span className="text-xs text-slate-400">Live on public portal</span>
          </div>
          <div className={`p-4 rounded-xl border ${isDark ? 'bg-slate-800/40 border-slate-800' : 'bg-slate-50/70 border-slate-200'}`}>
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Featured Posts</span>
            <div className="text-2xl font-bold mt-1 text-amber-500">
              {articles.filter((a) => a.feature === 1).length}
            </div>
            <span className="text-xs text-slate-400">Spotlight hero display</span>
          </div>
          <div className={`p-4 rounded-xl border ${isDark ? 'bg-slate-800/40 border-slate-800' : 'bg-slate-50/70 border-slate-200'}`}>
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Home Showcase</span>
            <div className="text-2xl font-bold mt-1 text-blue-500">
              {articles.filter((a) => a.homepage_status === 1).length}
            </div>
            <span className="text-xs text-slate-400">Homepage grid</span>
          </div>
          <div className={`p-4 rounded-xl border ${isDark ? 'bg-slate-800/40 border-slate-800' : 'bg-slate-50/70 border-slate-200'}`}>
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Pending Comments</span>
            <div className="text-2xl font-bold mt-1 text-rose-500">
              {comments.filter((c) => c.status === 0).length}
            </div>
            <span className="text-xs text-slate-400">Awaiting moderation</span>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 mb-6 overflow-x-auto">
        <button
          onClick={() => setActiveTab('articles')}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition -mb-px ${
            activeTab === 'articles'
              ? 'border-rose-500 text-rose-600 dark:text-rose-400'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          <BookOpen className="w-4 h-4" />
          Articles Directory ({totalArticles})
        </button>

        <button
          onClick={() => setActiveTab('editor')}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition -mb-px ${
            activeTab === 'editor'
              ? 'border-rose-500 text-rose-600 dark:text-rose-400'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          <Edit3 className="w-4 h-4" />
          {editingBlogId ? `Editing Article #${editingBlogId}` : 'Write Article'}
        </button>

        <button
          onClick={() => setActiveTab('categories')}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition -mb-px ${
            activeTab === 'categories'
              ? 'border-rose-500 text-rose-600 dark:text-rose-400'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          <FolderPlus className="w-4 h-4" />
          Categories & Tags ({categories.length} / {tags.length})
        </button>

        <button
          onClick={() => setActiveTab('authors')}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition -mb-px ${
            activeTab === 'authors'
              ? 'border-rose-500 text-rose-600 dark:text-rose-400'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          <UserPlus className="w-4 h-4" />
          Authors & Contributors ({authors.length})
        </button>

        <button
          onClick={() => setActiveTab('comments')}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition -mb-px ${
            activeTab === 'comments'
              ? 'border-rose-500 text-rose-600 dark:text-rose-400'
              : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          Comments Moderation
        </button>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: ARTICLES DIRECTORY & QUICK CONTROLS                                */}
      {/* ========================================================================= */}
      {activeTab === 'articles' && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className={`p-4 rounded-xl border flex flex-col md:flex-row items-center justify-between gap-4 ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
            <div className="flex-1 relative w-full md:w-auto">
              <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
              <input
                type="text"
                placeholder="Search by article title (English or Hindi) or excerpt..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                className={`w-full pl-9 pr-4 py-2 text-sm rounded-lg border outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 ${
                  isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-200 text-slate-800'
                }`}
              />
            </div>

            <div className="flex items-center gap-3 w-full md:w-auto">
              <select
                value={selectedCategoryFilter}
                onChange={(e) => {
                  setSelectedCategoryFilter(e.target.value);
                  setPage(1);
                }}
                className={`px-3 py-2 text-sm rounded-lg border outline-none ${
                  isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-200 text-slate-800'
                }`}
              >
                <option value="all">All Categories</option>
                {categories.map((c) => (
                  <option key={c.blog_category_id} value={c.blog_category_id.toString()}>
                    {c.name}
                  </option>
                ))}
              </select>

              <select
                value={selectedStatusFilter}
                onChange={(e) => {
                  setSelectedStatusFilter(e.target.value);
                  setPage(1);
                }}
                className={`px-3 py-2 text-sm rounded-lg border outline-none ${
                  isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-200 text-slate-800'
                }`}
              >
                <option value="all">All Statuses</option>
                <option value="1">Active / Live</option>
                <option value="0">Draft / Inactive</option>
              </select>

              <button
                onClick={() => fetchArticles()}
                title="Refresh Articles"
                className={`p-2 rounded-lg border hover:bg-slate-100 dark:hover:bg-slate-800 transition ${
                  isDark ? 'border-slate-700 text-slate-300' : 'border-slate-200 text-slate-600'
                }`}
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Articles Table */}
          <div className={`rounded-xl border overflow-hidden shadow-sm ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className={`border-b text-xs font-semibold uppercase tracking-wider ${isDark ? 'bg-slate-800/60 border-slate-800 text-slate-400' : 'bg-slate-50 border-slate-200 text-slate-500'}`}>
                  <tr>
                    <th className="py-3.5 px-4">Article Title & Metadata</th>
                    <th className="py-3.5 px-4">Categories & Tags</th>
                    <th className="py-3.5 px-4 text-center">Status</th>
                    <th className="py-3.5 px-4 text-center">Featured</th>
                    <th className="py-3.5 px-4 text-center">Homepage</th>
                    <th className="py-3.5 px-4 text-center">Views</th>
                    <th className="py-3.5 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {isLoadingArticles ? (
                    <tr>
                      <td colSpan={7} className="text-center py-12 text-slate-400">
                        <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-rose-500" />
                        Loading articles from database...
                      </td>
                    </tr>
                  ) : articles.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="text-center py-12 text-slate-400">
                        <BookOpen className="w-10 h-10 mx-auto mb-3 opacity-30 text-rose-500" />
                        No blog articles match your filters. Click "Write New Article" to create your first article!
                      </td>
                    </tr>
                  ) : (
                    articles.map((item) => (
                      <tr key={item.blog_id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition">
                        <td className="py-3.5 px-4">
                          <div className="flex items-start gap-3">
                            <img
                              src={item.image || 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=150'}
                              alt={item.blog_title}
                              className="w-14 h-14 rounded-lg object-cover border border-slate-200 dark:border-slate-700 flex-shrink-0"
                            />
                            <div>
                              <div className="font-semibold text-slate-900 dark:text-white line-clamp-1">
                                {item.blog_title}
                              </div>
                              <div className="text-xs text-slate-400 mt-1 flex items-center gap-2">
                                <span>Slug: /{item.slug}</span>
                                <span>•</span>
                                <span>{new Date(item.created_date).toLocaleDateString()}</span>
                              </div>
                            </div>
                          </div>
                        </td>

                        <td className="py-3.5 px-4">
                          <div className="flex flex-wrap gap-1 max-w-[200px]">
                            {item.category_names?.map((cName, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-0.5 rounded text-[11px] font-medium bg-rose-50 text-rose-600 dark:bg-rose-950/40 dark:text-rose-400"
                              >
                                {cName}
                              </span>
                            ))}
                            {item.tag_names?.map((tName, idx) => (
                              <span
                                key={idx}
                                className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                              >
                                #{tName}
                              </span>
                            ))}
                          </div>
                        </td>

                        {/* 1-Click Status Switch */}
                        <td className="py-3.5 px-4 text-center">
                          <button
                            onClick={() => handleToggle(item.blog_id, 'status', item.status)}
                            className={`px-3 py-1 rounded-full text-xs font-semibold transition ${
                              item.status === 1
                                ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-400'
                                : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400'
                            }`}
                          >
                            {item.status === 1 ? 'Live' : 'Draft'}
                          </button>
                        </td>

                        {/* 1-Click Feature Switch */}
                        <td className="py-3.5 px-4 text-center">
                          <button
                            onClick={() => handleToggle(item.blog_id, 'feature', item.feature)}
                            title="Toggle featured spotlight"
                            className={`p-1.5 rounded-lg transition ${
                              item.feature === 1
                                ? 'bg-amber-100 text-amber-600 dark:bg-amber-950/60 dark:text-amber-400'
                                : 'text-slate-300 hover:text-slate-500 dark:text-slate-600'
                            }`}
                          >
                            <Star className={`w-4 h-4 ${item.feature === 1 ? 'fill-amber-500' : ''}`} />
                          </button>
                        </td>

                        {/* 1-Click Homepage Switch */}
                        <td className="py-3.5 px-4 text-center">
                          <button
                            onClick={() => handleToggle(item.blog_id, 'homepage_status', item.homepage_status)}
                            title="Toggle homepage display"
                            className={`p-1.5 rounded-lg transition ${
                              item.homepage_status === 1
                                ? 'bg-blue-100 text-blue-600 dark:bg-blue-950/60 dark:text-blue-400'
                                : 'text-slate-300 hover:text-slate-500 dark:text-slate-600'
                            }`}
                          >
                            <Home className="w-4 h-4" />
                          </button>
                        </td>

                        {/* Total Views */}
                        <td className="py-3.5 px-4 text-center font-medium text-slate-700 dark:text-slate-300">
                          <div className="flex items-center justify-center gap-1">
                            <Eye className="w-3.5 h-3.5 text-slate-400" />
                            {item.total_view}
                          </div>
                        </td>

                        {/* Actions */}
                        <td className="py-3.5 px-4 text-right">
                          <div className="flex items-center justify-end gap-1">
                            <button
                              onClick={() => handleStartEdit(item)}
                              className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
                              title="Edit Article"
                            >
                              <Edit3 className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleDeleteArticle(item.blog_id)}
                              className="p-1.5 rounded hover:bg-rose-50 dark:hover:bg-rose-950/40 text-rose-500 transition"
                              title="Delete Article"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: RICH BILINGUAL ARTICLE EDITOR                                      */}
      {/* ========================================================================= */}
      {activeTab === 'editor' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold flex items-center gap-2">
              <Edit3 className="w-5 h-5 text-rose-500" />
              {editingBlogId ? `Edit Blog Article #${editingBlogId}` : 'Create New Dynamic Bilingual Article'}
            </h2>
            <div className="flex items-center gap-3">
              <button
                onClick={handleResetEditor}
                className="px-4 py-2 text-sm rounded-lg border hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition"
              >
                Clear Form
              </button>
              <button
                onClick={handleSaveArticle}
                disabled={isSavingArticle}
                className="flex items-center gap-2 px-6 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white font-medium text-sm shadow transition disabled:opacity-50"
              >
                {isSavingArticle ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                {editingBlogId ? 'Update Article' : 'Publish Article'}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Main Form (2 cols) */}
            <div className="lg:col-span-2 space-y-5">
              {/* Article Title & Slug */}
              <div className={`p-5 rounded-xl border space-y-4 ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
                <div>
                  <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
                    Article Title *
                  </label>
                  <input
                    type="text"
                    value={titleEn}
                    onChange={(e) => handleTitleChange(e.target.value)}
                    placeholder="e.g. Top 5 Real Estate Investment Corridors in Alwar 2026"
                    className={`w-full px-4 py-2.5 text-sm rounded-lg border font-medium outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 ${
                      isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-200 text-slate-800'
                    }`}
                  />
                </div>

                {/* Slug Generator */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      URL Slug *
                    </label>
                    <label className="text-xs text-rose-500 flex items-center gap-1 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={autoSlug}
                        onChange={(e) => setAutoSlug(e.target.checked)}
                        className="rounded text-rose-600 focus:ring-rose-500"
                      />
                      Auto-generate from Title
                    </label>
                  </div>
                  <div className="flex items-center">
                    <span className={`px-3 py-2 text-xs rounded-l-lg border border-r-0 ${isDark ? 'bg-slate-800 border-slate-700 text-slate-400' : 'bg-slate-100 border-slate-200 text-slate-500'}`}>
                      /blogs/
                    </span>
                    <input
                      type="text"
                      value={slug}
                      onChange={(e) => {
                        setAutoSlug(false);
                        setSlug(e.target.value);
                      }}
                      placeholder="top-5-real-estate-alwar-2026"
                      className={`flex-1 px-3 py-2 text-sm rounded-r-lg border outline-none font-mono text-xs focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 ${
                        isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-200 text-slate-800'
                      }`}
                    />
                  </div>
                </div>
              </div>

              {/* Excerpt & Full Article Content (Rich Text Editor) */}
              <div className={`p-5 rounded-xl border space-y-4 ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
                <div>
                  <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
                    Short Description / Excerpt *
                  </label>
                  <textarea
                    rows={3}
                    value={shortDesc}
                    onChange={(e) => setShortDesc(e.target.value)}
                    placeholder="A concise executive overview displayed in article listing cards and search snippets..."
                    className={`w-full px-4 py-2.5 text-sm rounded-lg border outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 ${
                      isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-200 text-slate-800'
                    }`}
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
                    Full Article Content (Rich Text Editor) *
                  </label>
                  <RichTextEditor
                    value={bodyEn}
                    onChange={setBodyEn}
                    placeholder="Write detailed market reports, format headings, add bullet points, insert hyperlinks, and embed photos..."
                    minHeight="420px"
                  />
                </div>
              </div>
            </div>

            {/* Sidebar Controls (1 col) */}
            <div className="space-y-5">
              {/* Featured Image Box */}
              <div className={`p-5 rounded-xl border space-y-3 ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
                <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Featured Image *
                </label>

                {featuredImage ? (
                  <div className="relative rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700">
                    <img src={featuredImage} alt="Featured" className="w-full h-40 object-cover" />
                    <button
                      onClick={() => setFeaturedImage('')}
                      className="absolute top-2 right-2 p-1 bg-black/60 hover:bg-black/80 rounded-full text-white transition"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition hover:border-rose-500 ${
                      isDark ? 'border-slate-700 bg-slate-800/40' : 'border-slate-300 bg-slate-50'
                    }`}
                  >
                    <UploadCloud className="w-8 h-8 text-rose-500 mx-auto mb-2" />
                    <div className="text-xs font-medium text-slate-700 dark:text-slate-300">
                      Click to upload photograph
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5">PNG, JPG, WEBP up to 10MB</div>
                  </div>
                )}

                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  accept="image/png, image/jpeg, image/webp"
                  className="hidden"
                />

                <input
                  type="text"
                  placeholder="Or paste external image URL..."
                  value={featuredImage}
                  onChange={(e) => setFeaturedImage(e.target.value)}
                  className={`w-full px-3 py-1.5 text-xs rounded border outline-none ${
                    isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-200 text-slate-800'
                  }`}
                />
              </div>

              {/* Taxonomy: Author, Categories, Tags */}
              <div className={`p-5 rounded-xl border space-y-4 ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
                {/* Author Select */}
                <div>
                  <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
                    Article Author *
                  </label>
                  <select
                    value={authorId}
                    onChange={(e) => setAuthorId(parseInt(e.target.value))}
                    className={`w-full px-3 py-2 text-sm rounded-lg border outline-none ${
                      isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-200 text-slate-800'
                    }`}
                  >
                    {authors.map((a) => (
                      <option key={a.author_id} value={a.author_id}>
                        {a.author_name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Categories Multi-Select Pills */}
                <div>
                  <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
                    Categories (Select at least 1) *
                  </label>
                  <div className="flex flex-wrap gap-1.5">
                    {categories.map((cat) => {
                      const isSelected = selectedCatIds.includes(cat.blog_category_id);
                      return (
                        <button
                          key={cat.blog_category_id}
                          type="button"
                          onClick={() => {
                            if (isSelected) {
                              setSelectedCatIds(selectedCatIds.filter((id) => id !== cat.blog_category_id));
                            } else {
                              setSelectedCatIds([...selectedCatIds, cat.blog_category_id]);
                            }
                          }}
                          className={`px-3 py-1 rounded-full text-xs font-medium transition ${
                            isSelected
                              ? 'bg-rose-500 text-white shadow-sm'
                              : isDark
                              ? 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                          }`}
                        >
                          {cat.name}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Tags Multi-Select Pills */}
                <div>
                  <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
                    Tags (Select at least 1) *
                  </label>
                  <div className="flex flex-wrap gap-1.5">
                    {tags.map((tag) => {
                      const isSelected = selectedTagIds.includes(tag.blog_tag_id);
                      return (
                        <button
                          key={tag.blog_tag_id}
                          type="button"
                          onClick={() => {
                            if (isSelected) {
                              setSelectedTagIds(selectedTagIds.filter((id) => id !== tag.blog_tag_id));
                            } else {
                              setSelectedTagIds([...selectedTagIds, tag.blog_tag_id]);
                            }
                          }}
                          className={`px-3 py-1 rounded-full text-xs font-medium transition ${
                            isSelected
                              ? 'bg-slate-800 text-white dark:bg-slate-200 dark:text-slate-900 shadow-sm'
                              : isDark
                              ? 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                              : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                          }`}
                        >
                          #{tag.name}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Visibility Controls */}
              <div className={`p-5 rounded-xl border space-y-3 ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
                <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Publishing Status
                </label>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Active / Live</span>
                  <input
                    type="checkbox"
                    checked={articleStatus === 1}
                    onChange={(e) => setArticleStatus(e.target.checked ? 1 : 0)}
                    className="w-4 h-4 text-rose-600 rounded"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Featured Spotlight</span>
                  <input
                    type="checkbox"
                    checked={articleFeature === 1}
                    onChange={(e) => setArticleFeature(e.target.checked ? 1 : 0)}
                    className="w-4 h-4 text-rose-600 rounded"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Display on Homepage</span>
                  <input
                    type="checkbox"
                    checked={articleHomepage === 1}
                    onChange={(e) => setArticleHomepage(e.target.checked ? 1 : 0)}
                    className="w-4 h-4 text-rose-600 rounded"
                  />
                </div>
              </div>

              {/* SEO Meta Tags Accordion */}
              <div className={`p-5 rounded-xl border space-y-3 ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
                <div className="text-xs font-semibold text-rose-600 uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4" />
                  Search Engine Optimization (SEO)
                </div>

                <div>
                  <label className="block text-xs text-slate-400 mb-1">
                    Meta Title ({metaTitle.length}/60 chars)
                  </label>
                  <input
                    type="text"
                    value={metaTitle}
                    onChange={(e) => setMetaTitle(e.target.value)}
                    placeholder={titleEn || 'SEO Title for Google SERP'}
                    className={`w-full px-3 py-1.5 text-xs rounded border outline-none ${
                      isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-200 text-slate-800'
                    }`}
                  />
                </div>

                <div>
                  <label className="block text-xs text-slate-400 mb-1">Meta Keywords (Comma separated)</label>
                  <input
                    type="text"
                    value={metaKeyword}
                    onChange={(e) => setMetaKeyword(e.target.value)}
                    placeholder="alwar plots, ncr real estate, jaipur express"
                    className={`w-full px-3 py-1.5 text-xs rounded border outline-none ${
                      isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-200 text-slate-800'
                    }`}
                  />
                </div>

                <div>
                  <label className="block text-xs text-slate-400 mb-1">
                    Meta Description ({metaDescription.length}/160 chars)
                  </label>
                  <textarea
                    rows={2}
                    value={metaDescription}
                    onChange={(e) => setMetaDescription(e.target.value)}
                    placeholder="Short snippet indexed by search crawlers..."
                    className={`w-full px-3 py-1.5 text-xs rounded border outline-none ${
                      isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-200 text-slate-800'
                    }`}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: CATEGORIES & TAGS MANAGEMENT                                       */}
      {/* ========================================================================= */}
      {activeTab === 'categories' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Categories Card */}
          <div className={`p-6 rounded-2xl border ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-lg flex items-center gap-2">
                <FolderPlus className="w-5 h-5 text-rose-500" />
                Blog Categories ({categories.length})
              </h3>
              <button
                onClick={() => setShowCategoryModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-50 text-rose-600 hover:bg-rose-100 dark:bg-rose-950/60 dark:text-rose-400 text-xs font-semibold transition"
              >
                <Plus className="w-4 h-4" /> Add Category
              </button>
            </div>

            <div className="divide-y divide-slate-100 dark:divide-slate-800">
              {categories.map((c) => (
                <div key={c.blog_category_id} className="py-3 flex items-center justify-between">
                  <div>
                    <div className="font-semibold text-sm">{c.name}</div>
                    <div className="text-xs text-slate-400 font-mono">/{c.slug}</div>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                      c.status === 1 ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {c.status === 1 ? 'Active' : 'Inactive'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Tags Cloud Card */}
          <div className={`p-6 rounded-2xl border ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-lg flex items-center gap-2">
                <Tag className="w-5 h-5 text-rose-500" />
                Blog Tags ({tags.length})
              </h3>
            </div>

            {/* Quick Add Tag Input */}
            <div className="flex items-center gap-2 mb-4">
              <input
                type="text"
                placeholder="Enter new tag name (e.g. Metro Expansion)..."
                value={newTagName}
                onChange={(e) => setNewTagName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleCreateTag()}
                className={`flex-1 px-3 py-2 text-sm rounded-lg border outline-none ${
                  isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-200 text-slate-800'
                }`}
              />
              <button
                onClick={handleCreateTag}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-sm font-semibold rounded-lg transition"
              >
                Add Tag
              </button>
            </div>

            <div className="flex flex-wrap gap-2 pt-2">
              {tags.map((t) => (
                <span
                  key={t.blog_tag_id}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border flex items-center gap-1.5 ${
                    isDark ? 'bg-slate-800/60 border-slate-700 text-slate-300' : 'bg-slate-50 border-slate-200 text-slate-700'
                  }`}
                >
                  <Tag className="w-3 h-3 text-rose-500" />
                  {t.name}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 4: AUTHORS & EDITORIAL PROFILES                                       */}
      {/* ========================================================================= */}
      {activeTab === 'authors' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-lg flex items-center gap-2">
              <UserPlus className="w-5 h-5 text-rose-500" />
              Editorial Authors & Market Experts ({authors.length})
            </h3>
            <button
              onClick={() => setShowAuthorModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-sm font-medium rounded-xl shadow transition"
            >
              <Plus className="w-4 h-4" /> Add Author Profile
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {authors.map((a) => (
              <div
                key={a.author_id}
                className={`p-5 rounded-2xl border shadow-sm transition hover:shadow-md ${
                  isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
                }`}
              >
                <div className="flex items-center gap-3">
                  <img
                    src={a.image || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150'}
                    alt={a.author_name}
                    className="w-14 h-14 rounded-full object-cover border-2 border-rose-500/20"
                  />
                  <div>
                    <h4 className="font-bold text-slate-900 dark:text-white">{a.author_name}</h4>
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold mt-0.5 ${
                        a.status === 1 ? 'bg-emerald-50 text-emerald-600' : 'bg-slate-100 text-slate-500'
                      }`}
                    >
                      {a.status === 1 ? 'Verified Contributor' : 'Inactive'}
                    </span>
                  </div>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-3 line-clamp-3 leading-relaxed">
                  {a.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 5: COMMENTS MODERATION QUEUE & THREADS                                */}
      {/* ========================================================================= */}
      {activeTab === 'comments' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCommentFilter(0)}
                className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition ${
                  commentFilter === 0
                    ? 'bg-rose-500 text-white shadow'
                    : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
                }`}
              >
                Pending Moderation ({comments.filter((c) => c.status === 0).length})
              </button>
              <button
                onClick={() => setCommentFilter(1)}
                className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition ${
                  commentFilter === 1
                    ? 'bg-rose-500 text-white shadow'
                    : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
                }`}
              >
                Approved & Live
              </button>
            </div>
            <button
              onClick={() => fetchComments()}
              className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          <div className="space-y-3">
            {isLoadingComments ? (
              <div className="text-center py-12 text-slate-400">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-rose-500" />
                Loading comments queue...
              </div>
            ) : comments.length === 0 ? (
              <div className="text-center py-12 text-slate-400">
                <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-30 text-rose-500" />
                No comments in this filter.
              </div>
            ) : (
              comments.map((comm) => (
                <div
                  key={comm.blog_comm_id}
                  className={`p-4 rounded-xl border space-y-3 ${
                    isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-bold text-sm text-slate-900 dark:text-white">{comm.name}</span>
                      <span className="text-xs text-slate-400 ml-2">({comm.email})</span>
                      {comm.comment_by === 'admin' && (
                        <span className="ml-2 px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-400">
                          Official Admin
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-slate-400">
                      {new Date(comm.created_date).toLocaleString()}
                    </span>
                  </div>

                  <p className="text-sm text-slate-700 dark:text-slate-300 bg-slate-50 dark:bg-slate-800/40 p-3 rounded-lg">
                    {comm.comment}
                  </p>

                  <div className="flex items-center justify-between pt-1">
                    <div className="flex items-center gap-2">
                      {comm.status === 0 ? (
                        <button
                          onClick={() => handleModerateComment(comm.blog_comm_id, 1)}
                          className="flex items-center gap-1.5 px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold transition"
                        >
                          <Check className="w-3.5 h-3.5" /> Approve Comment
                        </button>
                      ) : (
                        <button
                          onClick={() => handleModerateComment(comm.blog_comm_id, 0)}
                          className="flex items-center gap-1.5 px-3 py-1 rounded bg-amber-500 hover:bg-amber-600 text-white text-xs font-semibold transition"
                        >
                          Unapprove / Hide
                        </button>
                      )}
                      <button
                        onClick={() => handleDeleteComment(comm.blog_comm_id)}
                        className="px-3 py-1 rounded bg-rose-50 text-rose-600 hover:bg-rose-100 dark:bg-rose-950/60 dark:text-rose-400 text-xs font-semibold transition"
                      >
                        Delete
                      </button>
                    </div>

                    <button
                      onClick={() => setReplyingToComment(comm)}
                      className="flex items-center gap-1.5 text-xs text-rose-500 hover:text-rose-600 font-semibold"
                    >
                      <CornerDownRight className="w-3.5 h-3.5" /> Reply as Admin
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Admin Reply Modal */}
      {replyingToComment && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className={`w-full max-w-lg p-6 rounded-2xl border shadow-2xl space-y-4 ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-base flex items-center gap-2">
                <CornerDownRight className="w-4 h-4 text-rose-500" />
                Reply to {replyingToComment.name}
              </h3>
              <button onClick={() => setReplyingToComment(null)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="text-xs text-slate-500 p-3 bg-slate-50 dark:bg-slate-800/40 rounded-lg">
              "{replyingToComment.comment}"
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1">Official Response</label>
              <textarea
                rows={4}
                value={adminReplyText}
                onChange={(e) => setAdminReplyText(e.target.value)}
                placeholder="Type official response from Propira Omshiv Real Estate desk..."
                className={`w-full p-3 text-sm rounded-lg border outline-none ${
                  isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-200 text-slate-800'
                }`}
              />
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={() => setReplyingToComment(null)}
                className="px-4 py-2 text-xs font-semibold rounded-lg border text-slate-500"
              >
                Cancel
              </button>
              <button
                onClick={handleSendAdminReply}
                disabled={isSendingReply}
                className="flex items-center gap-2 px-5 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold rounded-lg transition"
              >
                <Send className="w-3.5 h-3.5" />
                Post Reply
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Category Modal */}
      {showCategoryModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className={`w-full max-w-md p-6 rounded-2xl border shadow-2xl space-y-4 ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-base">Create Blog Category</h3>
              <button onClick={() => setShowCategoryModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1">Category Name *</label>
              <input
                type="text"
                value={newCatName}
                onChange={(e) => {
                  setNewCatName(e.target.value);
                  setNewCatSlug(e.target.value.toLowerCase().replace(/\s+/g, '-'));
                }}
                placeholder="e.g. Legal & Documentation"
                className={`w-full px-3 py-2 text-sm rounded-lg border outline-none ${
                  isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-200 text-slate-800'
                }`}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1">Slug</label>
              <input
                type="text"
                value={newCatSlug}
                onChange={(e) => setNewCatSlug(e.target.value)}
                placeholder="legal-documentation"
                className={`w-full px-3 py-2 text-sm rounded-lg border outline-none ${
                  isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-200 text-slate-800'
                }`}
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setShowCategoryModal(false)} className="px-4 py-2 text-xs font-semibold rounded-lg border text-slate-500">
                Cancel
              </button>
              <button onClick={handleCreateCategory} className="px-5 py-2 bg-rose-600 text-white text-xs font-semibold rounded-lg">
                Create
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Author Modal */}
      {showAuthorModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className={`w-full max-w-md p-6 rounded-2xl border shadow-2xl space-y-4 ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-base">Add Author Profile</h3>
              <button onClick={() => setShowAuthorModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1">Full Name *</label>
              <input
                type="text"
                value={newAuthorName}
                onChange={(e) => setNewAuthorName(e.target.value)}
                placeholder="e.g. Ramesh Chandra"
                className={`w-full px-3 py-2 text-sm rounded-lg border outline-none ${
                  isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-200 text-slate-800'
                }`}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1">Bio / Designation *</label>
              <textarea
                rows={3}
                value={newAuthorDesc}
                onChange={(e) => setNewAuthorDesc(e.target.value)}
                placeholder="Senior Property Analyst with 10+ years covering Alwar & Neemrana belt..."
                className={`w-full px-3 py-2 text-sm rounded-lg border outline-none ${
                  isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-200 text-slate-800'
                }`}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 mb-1">Photo URL</label>
              <input
                type="text"
                value={newAuthorImage}
                onChange={(e) => setNewAuthorImage(e.target.value)}
                placeholder="/uploads/authors/ramesh.jpg"
                className={`w-full px-3 py-2 text-sm rounded-lg border outline-none ${
                  isDark ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-200 text-slate-800'
                }`}
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setShowAuthorModal(false)} className="px-4 py-2 text-xs font-semibold rounded-lg border text-slate-500">
                Cancel
              </button>
              <button onClick={handleCreateAuthor} className="px-5 py-2 bg-rose-600 text-white text-xs font-semibold rounded-lg">
                Save Author
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default BlogManager;
