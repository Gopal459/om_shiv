import React, { useState } from 'react';
import {
  Flame,
  Phone,
  MessageSquare,
  Clock,
  MapPin,
  User,
  ChevronRight,
  GripVertical,
  ArrowDown,
  Bookmark,
  TrendingUp,
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
  created_date?: string | null;
  requirement_title?: string;
  source_name?: string;
  assigned_to?: string | null;
  assigned_to_name?: string;
  followup_datetime?: string | null;
  current_update?: string;
  status_label?: string;
}

const formatCardDate = (iso?: string | null): string => {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  const parts = new Intl.DateTimeFormat('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    timeZone: 'Asia/Kolkata',
  }).formatToParts(d);
  const day = parts.find((p) => p.type === 'day')?.value ?? '';
  const month = parts.find((p) => p.type === 'month')?.value ?? '';
  const year = parts.find((p) => p.type === 'year')?.value ?? '';
  return `${day}-${month}-${year}`;
};

const formatCardDateTime = (iso?: string | null): string => {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  const datePart = formatCardDate(iso);
  const timePart = new Intl.DateTimeFormat('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
    timeZone: 'Asia/Kolkata',
  }).format(d);
  return `${datePart} ${timePart}`;
};

const formatINRCompact = (amount: number): string => {
  if (amount >= 10_000_000) return `₹${(amount / 10_000_000).toFixed(2)} Cr`;
  if (amount >= 100_000) return `₹${(amount / 100_000).toFixed(2)} L`;
  return `₹${amount.toLocaleString('en-IN')}`;
};

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
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-[#F04B42] text-white shadow-2xs shrink-0">
          <Flame className="w-2.5 h-2.5" /> Hot
        </span>
      );
    }
    if (rating === 2) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold bg-amber-500 text-white shadow-2xs shrink-0">
          Warm
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold bg-slate-500 text-white shadow-2xs shrink-0">
        Cold
      </span>
    );
  };

  const getStatusPillClass = (colKey: string) => {
    switch (colKey) {
      case 'new':
        return 'bg-[#291BB0] text-white';
      case 'in_progress':
        return 'bg-indigo-600 text-white';
      case 'site_visit':
        return 'bg-purple-600 text-white';
      case 'qualified':
        return 'bg-teal-600 text-white';
      case 'converted':
        return 'bg-emerald-600 text-white';
      case 'disqualified':
        return 'bg-[#F04B42] text-white';
      default:
        return 'bg-[#291BB0] text-white';
    }
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
                  const dealPrice = Number(lead.deal_final_price || 0);
                  const headline =
                    lead.requirement_title ||
                    (lead.lead_remark && lead.lead_remark !== 'N/A'
                      ? lead.lead_remark
                      : `Interested For ${lead.lead_type} Property`);
                  const displayAddress = lead.address || lead.property_address || 'Alwar, Rajasthan';
                  const ownerLabel = lead.assigned_to_name || lead.source_name || 'Om Shiv Properties';
                  const followUpText = formatCardDateTime(lead.followup_datetime || lead.created_date);
                  const updateLabel =
                    lead.current_update ||
                    (lead.lead_remark && lead.lead_remark !== 'N/A' ? lead.lead_remark : 'General Follow-Up');
                  const statusLabel = lead.status_label || (col.key === 'new' ? 'New' : col.label);

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
                      className={`relative bg-white dark:bg-slate-800/95 rounded-2xl p-3.5 border shadow-xs transition-all duration-200 cursor-grab active:cursor-grabbing group hover:-translate-y-0.5 ${
                        isDragging
                          ? 'opacity-30 scale-95 border-2 border-dashed border-[#291BB0] bg-[#291BB0]/5 dark:bg-[#291BB0]/20 shadow-xl'
                          : isMoving
                          ? 'opacity-50 pointer-events-none animate-pulse border-amber-300'
                          : 'border-slate-200/90 dark:border-slate-700/80 hover:shadow-md hover:border-[#291BB0]/40 dark:hover:border-[#291BB0]/60'
                      }`}
                    >
                      {/* Row 1: Requirement Headline + Drag Grip + ID & Type */}
                      <div className="flex items-start justify-between gap-2 pb-2 mb-2 border-b border-slate-100 dark:border-slate-700/70">
                        <div className="flex items-center gap-1.5 min-w-0">
                          <span
                            title="Drag to move card"
                            className="text-slate-400 group-hover:text-[#291BB0] cursor-grab active:cursor-grabbing shrink-0"
                          >
                            <GripVertical className="w-3.5 h-3.5" />
                          </span>
                          <h4
                            title={headline}
                            className="text-[12.5px] font-extrabold text-slate-900 dark:text-white truncate group-hover:text-[#291BB0] dark:group-hover:text-indigo-300 transition-colors"
                          >
                            {headline}
                          </h4>
                        </div>

                        <div className="flex items-center gap-1 shrink-0">
                          <span className="font-mono text-[9.5px] font-bold px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700/80 text-slate-700 dark:text-slate-300">
                            {lead.lead_unique_id}
                          </span>
                          <span
                            className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase ${
                              lead.lead_type === 'BUY'
                                ? 'bg-[#291BB0]/10 dark:bg-[#291BB0]/30 text-[#291BB0] dark:text-indigo-300'
                                : lead.lead_type === 'RENT'
                                ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300'
                                : 'bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300'
                            }`}
                          >
                            {lead.lead_type}
                          </span>
                        </div>
                      </div>

                      {/* Row 2: Client Name + Created Date */}
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <div className="flex items-center gap-1.5 min-w-0">
                          <User className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          <span className="text-xs font-bold text-slate-800 dark:text-slate-100 truncate">
                            {lead.contact_name}
                          </span>
                        </div>
                        <span className="text-[10.5px] font-medium text-slate-500 dark:text-slate-400 shrink-0">
                          {formatCardDate(lead.created_date)}
                        </span>
                      </div>

                      {/* Row 3: Location Pin + Full Address & Deal Budget (strictly > 0) */}
                      <div className="flex items-center justify-between gap-2 text-[11px] text-slate-600 dark:text-slate-300 mb-2">
                        <div className="flex items-center gap-1.5 min-w-0">
                          <MapPin className="w-3.5 h-3.5 text-[#F04B42] shrink-0" />
                          <span title={displayAddress} className="truncate">
                            {displayAddress}
                          </span>
                        </div>
                        {dealPrice > 0 && (
                          <span className="text-[10.5px] font-bold text-emerald-600 dark:text-emerald-400 shrink-0">
                            {formatINRCompact(dealPrice)}
                          </span>
                        )}
                      </div>

                      {/* Row 4: Temperature Tag + Org/Assignee + Follow-up / Updated DateTime */}
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[10.5px] text-slate-500 dark:text-slate-400 mb-2">
                        {getTemperatureBadge(lead.rating)}
                        <span className="inline-flex items-center gap-1 text-slate-700 dark:text-slate-200 font-medium truncate max-w-[130px]">
                          <Bookmark className="w-3 h-3 text-[#291BB0] dark:text-indigo-400 shrink-0" />
                          <span className="truncate">{ownerLabel}</span>
                        </span>
                        <span className="inline-flex items-center gap-1 text-[10px] text-slate-500 dark:text-slate-400 ml-auto shrink-0">
                          <Clock className="w-3 h-3 shrink-0" />
                          <span>{followUpText}</span>
                        </span>
                      </div>

                      {/* Row 5: Current Update / Follow-Up Outcome + Status Pill */}
                      <div className="flex items-center justify-between gap-2 pb-2.5 border-b border-slate-100 dark:border-slate-700/70">
                        <div className="flex items-center gap-1.5 min-w-0 text-[11px] text-slate-600 dark:text-slate-300 font-medium">
                          <TrendingUp className="w-3.5 h-3.5 text-[#291BB0] dark:text-indigo-400 shrink-0" />
                          <span title={updateLabel} className="truncate">
                            {updateLabel}
                          </span>
                        </div>
                        <span
                          className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold shrink-0 shadow-2xs ${getStatusPillClass(
                            col.key
                          )}`}
                        >
                          {statusLabel}
                        </span>
                      </div>

                      {/* Row 6: Quick Actions Footer */}
                      <div className="pt-2 flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <a
                            href={`tel:${lead.mobile}`}
                            onClick={(e) => e.stopPropagation()}
                            title="Call Lead"
                            className="p-1.5 rounded-lg bg-[#291BB0]/10 dark:bg-[#291BB0]/30 text-[#291BB0] dark:text-indigo-300 hover:bg-[#291BB0] hover:text-white transition-colors"
                          >
                            <Phone className="w-3 h-3" />
                          </a>
                          <a
                            href={`https://wa.me/${lead.mobile.replace(/\D/g, '')}`}
                            target="_blank"
                            rel="noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            title="WhatsApp Chat"
                            className="p-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-600 hover:text-white transition-colors"
                          >
                            <MessageSquare className="w-3 h-3" />
                          </a>
                          <span className="text-[10px] font-mono text-slate-400 ml-1">
                            {lead.mobile}
                          </span>
                        </div>

                        {col.key !== 'converted' && col.key !== 'disqualified' && (
                          <button
                            type="button"
                            onClick={(e) => handleQuickAdvance(e, lead, col.key)}
                            title="Advance to Next Stage"
                            className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:bg-[#291BB0] hover:text-white transition-all text-[10px] font-bold cursor-pointer"
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
