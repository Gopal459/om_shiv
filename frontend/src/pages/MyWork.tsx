import React, { useEffect, useState, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Rocket,
  PlusCircle,
  FileSpreadsheet,
  Kanban,
  Table as TableIcon,
  RefreshCw,
  Clock,
  Flame,
  CheckCircle2,
  Filter,
} from 'lucide-react';
import { LeadKanbanBoard, KanbanLeadItem } from '../components/leads/LeadKanbanBoard';
import { LeadTableView } from '../components/leads/LeadTableView';
import { CreateLeadModal } from '../components/leads/CreateLeadModal';
import { ImportLeadModal } from '../components/leads/ImportLeadModal';

interface MyWorkProps {
  onSelectLead: (leadId: string) => void;
}

export const MyWork: React.FC<MyWorkProps> = ({ onSelectLead }) => {
  const location = useLocation();
  const navigate = useNavigate();

  // Parse URL search params
  const searchParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const urlType = searchParams.get('type') || 'all';
  const urlAction = searchParams.get('action');

  // UI States
  const [viewMode, setViewMode] = useState<'KANBAN' | 'TABLE'>('KANBAN');
  const [activeType, setActiveType] = useState<string>(urlType.toUpperCase());
  const [isCreateOpen, setIsCreateOpen] = useState(urlAction === 'create');
  const [isImportOpen, setIsImportOpen] = useState(urlAction === 'import');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Kanban Data State
  const [boardData, setBoardData] = useState<{
    new: KanbanLeadItem[];
    in_progress: KanbanLeadItem[];
    site_visit: KanbanLeadItem[];
    qualified: KanbanLeadItem[];
    converted: KanbanLeadItem[];
    disqualified: KanbanLeadItem[];
  }>({
    new: [],
    in_progress: [],
    site_visit: [],
    qualified: [],
    converted: [],
    disqualified: [],
  });

  // Sync state if URL query params change
  useEffect(() => {
    if (urlType) {
      setActiveType(urlType.toUpperCase());
    }
    if (urlAction === 'create') setIsCreateOpen(true);
    if (urlAction === 'import') setIsImportOpen(true);
  }, [urlType, urlAction]);

  const fetchKanbanData = async (isManual = false) => {
    if (isManual) setRefreshing(true);
    else setLoading(true);

    try {
      const token = localStorage.getItem('access_token');
      const paramType = activeType.toLowerCase();
      const query = paramType !== 'all' ? `?type=${paramType}` : '';

      const res = await fetch(`/v1/leads/kanban${query}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      if (res.ok) {
        const data = await res.json();
        setBoardData(data);
      }
    } catch (err) {
      console.error('Failed to load leads kanban', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchKanbanData();
  }, [activeType]);

  const handleStageChange = async (
    leadId: string,
    newStatus: number,
    newStage?: number,
    toColumnKey?: string
  ) => {
    // Optimistic UI update: instantly move the lead into the target column
    const previousBoard = { ...boardData };
    if (toColumnKey) {
      setBoardData((prev: any) => {
        let movedCard: any = null;
        const nextBoard: any = {};
        for (const k of Object.keys(prev)) {
          const found = prev[k].find((item: any) => item.lead_unique_id === leadId);
          if (found) {
            movedCard = { ...found, lead_status: newStatus, stage: newStage ?? 1 };
            nextBoard[k] = prev[k].filter((item: any) => item.lead_unique_id !== leadId);
          } else {
            nextBoard[k] = prev[k];
          }
        }
        if (movedCard && nextBoard[toColumnKey]) {
          nextBoard[toColumnKey] = [movedCard, ...nextBoard[toColumnKey]];
        }
        return nextBoard;
      });
    }

    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`/v1/leads/${leadId}/stage`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          lead_status: newStatus,
          stage: newStage ?? 1,
        }),
      });

      if (res.ok) {
        // Silently re-sync to get official state from server
        fetchKanbanData(true);
      } else {
        // Rollback
        setBoardData(previousBoard);
      }
    } catch (err) {
      console.error('Failed to advance stage', err);
      setBoardData(previousBoard);
    }
  };

  // Flatten leads for table view
  const allLeadsList = useMemo(() => {
    return [
      ...boardData.new,
      ...boardData.in_progress,
      ...boardData.site_visit,
      ...boardData.qualified,
      ...boardData.converted,
      ...boardData.disqualified,
    ];
  }, [boardData]);

  const handleTypeTabChange = (type: string) => {
    setActiveType(type);
    navigate(`/leads?type=${type.toLowerCase()}`, { replace: true });
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Top Header & Action Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-2 rounded-xl bg-rose-500/10 text-rose-500 border border-rose-500/20">
              <Rocket className="w-5 h-5" />
            </span>
            <h1 className="text-xl sm:text-2xl font-black text-slate-900 dark:text-white tracking-tight">
              Enterprise Leads Command Center
            </h1>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            6-way inbound lead routing, interactive Kanban pipeline, 3-hour SLA tracking, and bulk import
          </p>
        </div>

        {/* Action Buttons & View Mode Toggle */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* View Mode Switcher */}
          <div className="p-1 rounded-2xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center">
            <button
              type="button"
              onClick={() => setViewMode('KANBAN')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                viewMode === 'KANBAN'
                  ? 'bg-white dark:bg-slate-900 text-rose-600 dark:text-rose-400 shadow-xs'
                  : 'text-slate-500 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Kanban className="w-3.5 h-3.5" />
              <span>Kanban</span>
            </button>

            <button
              type="button"
              onClick={() => setViewMode('TABLE')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                viewMode === 'TABLE'
                  ? 'bg-white dark:bg-slate-900 text-rose-600 dark:text-rose-400 shadow-xs'
                  : 'text-slate-500 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <TableIcon className="w-3.5 h-3.5" />
              <span>Table</span>
            </button>
          </div>

          {/* Quick Refresh */}
          <button
            onClick={() => fetchKanbanData(true)}
            disabled={refreshing}
            title="Refresh Leads"
            className="p-2.5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 hover:text-rose-500 transition-colors shadow-xs"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin text-rose-500' : ''}`} />
          </button>

          {/* Bulk Import */}
          <button
            onClick={() => setIsImportOpen(true)}
            className="flex items-center gap-2 px-3.5 py-2.5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs font-bold transition-all shadow-xs"
          >
            <FileSpreadsheet className="w-4 h-4 text-blue-500" />
            <span>Import Leads</span>
          </button>

          {/* Create Lead */}
          <button
            onClick={() => setIsCreateOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-gradient-to-r from-rose-500 to-rose-600 hover:from-rose-600 hover:to-rose-700 text-white text-xs font-bold transition-all shadow-md shadow-rose-500/20 active:scale-95"
          >
            <PlusCircle className="w-4 h-4" />
            <span>+ Create Lead</span>
          </button>
        </div>
      </div>

      {/* Property Type Filter Tabs (Buy, Rent, PG) */}
      <div className="flex items-center justify-between gap-3 overflow-x-auto pb-1">
        <div className="flex items-center gap-2">
          {[
            { id: 'ALL', label: 'All Inflows', count: allLeadsList.length },
            { id: 'BUY', label: 'Buy Properties', count: allLeadsList.filter((l) => l.lead_type === 'BUY').length },
            { id: 'RENT', label: 'Rental Inquiries', count: allLeadsList.filter((l) => l.lead_type === 'RENT').length },
            { id: 'PG', label: 'Paying Guest (PG)', count: allLeadsList.filter((l) => l.lead_type === 'PG').length },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => handleTypeTabChange(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-2xl text-xs font-bold transition-all border ${
                activeType === tab.id
                  ? 'bg-rose-500 text-white border-rose-500 shadow-sm'
                  : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:border-slate-300'
              }`}
            >
              <span>{tab.label}</span>
              <span
                className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                  activeType === tab.id
                    ? 'bg-white/20 text-white'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-500'
                }`}
              >
                {tab.count}
              </span>
            </button>
          ))}
        </div>

        {/* 3-Hour SLA Escalation Indicator */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-50 dark:bg-amber-950/60 border border-amber-200 dark:border-amber-900 text-amber-700 dark:text-amber-400 text-xs font-bold">
          <Clock className="w-3.5 h-3.5 animate-pulse" />
          <span>3-Hour SLA Rule Active</span>
        </div>
      </div>

      {/* View Content (Kanban or Table) */}
      {viewMode === 'KANBAN' ? (
        <LeadKanbanBoard
          boardData={boardData}
          onSelectLead={onSelectLead}
          onStageChange={handleStageChange}
          loading={loading}
        />
      ) : (
        <LeadTableView
          leads={allLeadsList}
          onSelectLead={onSelectLead}
          loading={loading}
        />
      )}

      {/* Inflow Modals */}
      <CreateLeadModal
        isOpen={isCreateOpen}
        onClose={() => {
          setIsCreateOpen(false);
          if (urlAction === 'create') navigate('/leads', { replace: true });
        }}
        onCreated={() => fetchKanbanData(true)}
        defaultType={activeType !== 'ALL' ? activeType : 'BUY'}
      />

      <ImportLeadModal
        isOpen={isImportOpen}
        onClose={() => {
          setIsImportOpen(false);
          if (urlAction === 'import') navigate('/leads', { replace: true });
        }}
        onImported={() => fetchKanbanData(true)}
      />
    </div>
  );
};

export default MyWork;
