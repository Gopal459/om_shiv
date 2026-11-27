import React, { useState } from 'react';
import {
  Flame,
  Phone,
  MessageSquare,
  ArrowRight,
  MoreVertical,
  Clock,
  MapPin,
  CheckCircle2,
  AlertCircle,
  Building,
  User,
  ChevronRight,
  ExternalLink,
  GripVertical,
  ArrowDown,
  Sparkles,
} from 'lucide-react';

export interface KanbanLeadItem {
  leads_id: number;
  lead_unique_id: string;
  contact_name: string;
  mobile: string;
  email?: string | null;
  address?: string | null;
  lead_type: string;
  rating: number; // 1-Hot, 2-Warm, 3-Cold
  lead_status: number;
  stage: number;
  property_address: string;
  deal_final_price?: number;
  lead_remark?: string;
  created_date?: string;
}

interface LeadKanbanBoardProps {
  boardData: {
    new: KanbanLeadItem[];
    in_progress: KanbanLeadItem[];
    site_visit: KanbanLeadItem[];
    qualified: KanbanLeadItem[];
    converted: KanbanLeadItem[];
    disqualified: KanbanLeadItem[];
  };
  onSelectLead: (leadId: string) => void;
  onStageChange: (leadId: string, newStatus: number, newStage?: number, toColumnKey?: string) => Promise<void>;
  loading?: boolean;
}

export const COLUMNS = [
  { key: 'new', label: 'New Intake', status: 0, stage: 1, color: 'border-blue-500 text-blue-600 bg-blue-500/10' },
  { key: 'in_progress', label: 'In Progress', status: 1, stage: 1, color: 'border-indigo-500 text-indigo-600 bg-indigo-500/10' },
  { key: 'site_visit', label: 'Site Visit / Inspection', status: 1, stage: 2, color: 'border-purple-500 text-purple-600 bg-purple-500/10' },
  { key: 'qualified', label: 'Qualified Deals', status: 4, stage: 1, color: 'border-teal-500 text-teal-600 bg-teal-500/10' },
  { key: 'converted', label: 'Deal Closed / Won', status: 5, stage: 3, color: 'border-emerald-500 text-emerald-600 bg-emerald-500/10' },
  { key: 'disqualified', label: 'Disqualified / Lost', status: 2, stage: 1, color: 'border-rose-500 text-rose-600 bg-rose-500/10' },
] as const;

export const LeadKanbanBoard: React.FC<LeadKanbanBoardProps> = ({
  boardData,
  onSelectLead,
  onStageChange,
  loading = false,
}) => {
  const [movingLeadId, setMovingLeadId] = useState<string | null>(null);
  const [draggedLead, setDraggedLead] = useState<{ leadId: string; fromColumn: string } | null>(null);
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null);
  const [justDragged, setJustDragged] = useState(false);

  const getTemperatureBadge = (rating: number) => {
    if (rating === 1) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-rose-100 dark:bg-rose-950/80 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-800">
          <Flame className="w-3 h-3 text-rose-600 dark:text-rose-400" /> HOT
        </span>
      );
    }
    if (rating === 2) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold bg-amber-100 dark:bg-amber-950/80 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800">
          WARM
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
        COLD
      </span>
    );
  };

  const handleQuickAdvance = async (e: React.MouseEvent, lead: KanbanLeadItem, currentColumnKey: string) => {
    e.stopPropagation();
    const colIndex = COLUMNS.findIndex((c) => c.key === currentColumnKey);
    if (colIndex >= 0 && colIndex < COLUMNS.length - 1) {
      const nextCol = COLUMNS[colIndex + 1];
      setMovingLeadId(lead.lead_unique_id);
      try {
        await onStageChange(lead.lead_unique_id, nextCol.status, nextCol.stage, nextCol.key);
      } finally {
        setMovingLeadId(null);
      }
    }
  };

  // Drag and Drop handlers
  const handleDragStart = (e: React.DragEvent, lead: KanbanLeadItem, fromColumn: string) => {
    e.dataTransfer.setData(
      'application/json',
      JSON.stringify({ leadId: lead.lead_unique_id, fromColumn })
    );
    e.dataTransfer.setData('text/plain', lead.lead_unique_id);
    e.dataTransfer.effectAllowed = 'move';
    setDraggedLead({ leadId: lead.lead_unique_id, fromColumn });
  };

  const handleDragEnd = () => {
    setDraggedLead(null);
    setDragOverColumn(null);
    setJustDragged(true);
    setTimeout(() => setJustDragged(false), 200);
  };

  const handleDragOverColumn = (e: React.DragEvent, columnKey: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (dragOverColumn !== columnKey) {
      setDragOverColumn(columnKey);
    }
  };

  const handleDragEnterColumn = (e: React.DragEvent, columnKey: string) => {
    e.preventDefault();
    if (draggedLead && draggedLead.fromColumn !== columnKey) {
      setDragOverColumn(columnKey);
    }
  };

  const handleDragLeaveColumn = (e: React.DragEvent) => {
    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
      setDragOverColumn((prev) => (prev ? null : prev));
    }
  };

  const handleDropOnColumn = async (e: React.DragEvent, targetCol: typeof COLUMNS[number]) => {
    e.preventDefault();
    setDragOverColumn(null);

    let leadId = draggedLead?.leadId;
    let fromColumn = draggedLead?.fromColumn;

    try {
      const jsonStr = e.dataTransfer.getData('application/json');
      if (jsonStr) {
        const parsed = JSON.parse(jsonStr);
        leadId = parsed.leadId || leadId;
        fromColumn = parsed.fromColumn || fromColumn;
      }
    } catch {
      // Fallback to text/plain
      const text = e.dataTransfer.getData('text/plain');
      if (text) leadId = text;
    }

    if (!leadId) return;

    // Only move if target column is different from source
    if (fromColumn !== targetCol.key) {
      setMovingLeadId(leadId);
      try {
        await onStageChange(leadId, targetCol.status, targetCol.stage, targetCol.key);
      } finally {
        setMovingLeadId(null);
        setDraggedLead(null);
      }
    }
  };

  return (
    <div className="flex gap-4 overflow-x-auto pb-6 pt-2 custom-scrollbar select-none min-h-[620px]">
      {COLUMNS.map((col) => {
        const items = (boardData as any)[col.key] || [];
        const isDragTarget = dragOverColumn === col.key && draggedLead && draggedLead.fromColumn !== col.key;

        return (
          <div
            key={col.key}
            onDragOver={(e) => handleDragOverColumn(e, col.key)}
            onDragEnter={(e) => handleDragEnterColumn(e, col.key)}
            onDragLeave={handleDragLeaveColumn}
            onDrop={(e) => handleDropOnColumn(e, col)}
            className={`w-80 flex-shrink-0 flex flex-col rounded-3xl border transition-all duration-200 overflow-hidden ${
              isDragTarget
                ? 'bg-emerald-50/80 dark:bg-emerald-950/30 border-emerald-400 ring-2 ring-emerald-500/60 shadow-lg scale-[1.01]'
                : 'bg-slate-50/70 dark:bg-slate-900/60 border-slate-200/80 dark:border-slate-800 shadow-xs'
            }`}
          >
            {/* Column Header */}
            <div
              className={`p-4 border-b border-slate-200/80 dark:border-slate-800 flex items-center justify-between bg-white dark:bg-slate-900 border-t-4 ${
                col.color.split(' ')[0]
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-900 dark:text-white">
                  {col.label}
                </span>
                <span
                  className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${col.color
                    .split(' ')
                    .slice(1)
                    .join(' ')}`}
                >
                  {items.length}
                </span>
              </div>

              {isDragTarget && (
                <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 animate-pulse flex items-center gap-1">
                  <ArrowDown className="w-3 h-3" /> Drop here
                </span>
              )}
            </div>

            {/* Cards List / Drop Target */}
            <div className="flex-1 p-3 space-y-3 overflow-y-auto max-h-[720px] custom-scrollbar flex flex-col">
              {/* Drop Target Indicator when dragging over this column */}
              {isDragTarget && (
                <div className="p-3.5 rounded-2xl border-2 border-dashed border-emerald-500 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 text-xs font-bold text-center flex items-center justify-center gap-2 animate-pulse shadow-xs">
                  <ArrowDown className="w-4 h-4 text-emerald-600 animate-bounce" />
                  <span>Release to move card to {col.label}</span>
                </div>
              )}

              {loading && items.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-400">Loading column...</div>
              ) : items.length === 0 ? (
                <div className="py-12 px-4 text-center rounded-2xl border border-dashed border-slate-200 dark:border-slate-800/80 text-slate-400 text-xs flex-1 flex flex-col items-center justify-center gap-1">
                  <p className="font-medium">No leads in {col.label.toLowerCase()}</p>
                  <p className="text-[10px] text-slate-400">Drag cards here to update stage</p>
                </div>
              ) : (
                items.map((lead: KanbanLeadItem) => {
                  const isMoving = movingLeadId === lead.lead_unique_id;
                  const isDragging = draggedLead?.leadId === lead.lead_unique_id;

                  return (
                    <div
                      key={lead.lead_unique_id}
                      draggable={!isMoving}
                      onDragStart={(e) => handleDragStart(e, lead, col.key)}
                      onDragEnd={handleDragEnd}
                      onClick={() => {
                        if (!justDragged) {
                          onSelectLead(lead.lead_unique_id);
                        }
                      }}
                      className={`relative bg-white dark:bg-slate-800/90 rounded-2xl p-4 border shadow-xs transition-all duration-200 cursor-grab active:cursor-grabbing group hover:-translate-y-0.5 ${
                        isDragging
                          ? 'opacity-30 scale-95 border-2 border-dashed border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/40 shadow-xl'
                          : isMoving
                          ? 'opacity-50 pointer-events-none animate-pulse border-amber-300'
                          : 'border-slate-200/80 dark:border-slate-700/80 hover:shadow-md hover:border-slate-300 dark:hover:border-slate-600'
                      }`}
                    >
                      {/* Top Badges & Drag Grip */}
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <div className="flex items-center gap-1.5">
                          <span
                            title="Drag to move card"
                            className="text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-300 cursor-grab active:cursor-grabbing"
                          >
                            <GripVertical className="w-3.5 h-3.5" />
                          </span>

                          <span className="font-mono text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-700/80 text-slate-700 dark:text-slate-300">
                            {lead.lead_unique_id}
                          </span>
                        </div>

                        <div className="flex items-center gap-1.5">
                          <span
                            className={`text-[9px] font-bold px-2 py-0.5 rounded uppercase ${
                              lead.lead_type === 'BUY'
                                ? 'bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300'
                                : lead.lead_type === 'RENT'
                                ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300'
                                : 'bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300'
                            }`}
                          >
                            {lead.lead_type}
                          </span>
                          {getTemperatureBadge(lead.rating)}
                        </div>
                      </div>

                      {/* Lead Title & Requirement */}
                      <h4 className="text-xs font-bold text-slate-900 dark:text-white line-clamp-1 group-hover:text-rose-500 transition-colors">
                        {lead.contact_name}
                      </h4>

                      <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-1 mt-0.5">
                        {lead.lead_remark && lead.lead_remark !== 'N/A'
                          ? lead.lead_remark
                          : `Inquiry for ${lead.lead_type} property`}
                      </p>

                      {/* Location & Budget */}
                      <div className="mt-3 pt-2.5 border-t border-slate-100 dark:border-slate-700/60 space-y-1 text-[11px] text-slate-500 dark:text-slate-400">
                        <div className="flex items-center gap-1.5 truncate">
                          <MapPin className="w-3 h-3 text-slate-400 flex-shrink-0" />
                          <span className="truncate">{lead.property_address || 'Alwar / Jaipur'}</span>
                        </div>

                        {lead.deal_final_price && lead.deal_final_price > 0 && (
                          <div className="flex items-center gap-1.5 font-semibold text-emerald-600 dark:text-emerald-400">
                            <span>₹ {lead.deal_final_price.toLocaleString('en-IN')}</span>
                          </div>
                        )}
                      </div>

                      {/* Card Footer: Quick Actions */}
                      <div className="mt-3 pt-2 flex items-center justify-between border-t border-slate-100 dark:border-slate-700/60">
                        <div className="flex items-center gap-1.5">
                          <a
                            href={`tel:${lead.mobile}`}
                            onClick={(e) => e.stopPropagation()}
                            title="Call Lead"
                            className="p-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 transition-colors"
                          >
                            <Phone className="w-3 h-3" />
                          </a>
                          <a
                            href={`https://wa.me/${lead.mobile.replace(/\D/g, '')}`}
                            target="_blank"
                            rel="noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            title="WhatsApp Chat"
                            className="p-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-100 transition-colors"
                          >
                            <MessageSquare className="w-3 h-3" />
                          </a>
                        </div>

                        {col.key !== 'converted' && col.key !== 'disqualified' && (
                          <button
                            type="button"
                            onClick={(e) => handleQuickAdvance(e, lead, col.key)}
                            title="Advance to Next Stage"
                            className="flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:bg-[#291BB0] hover:text-white transition-all text-[10px] font-bold"
                          >
                            <span>Next Stage</span>
                            <ChevronRight className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default LeadKanbanBoard;
