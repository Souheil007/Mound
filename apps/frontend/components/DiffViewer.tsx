"use client";

import { useState } from "react";
import { BlueprintVersion } from "@/lib/types";

interface DiffViewerProps {
  versions: BlueprintVersion[];
}

export default function DiffViewer({ versions }: DiffViewerProps) {
  if (versions.length < 2) {
    return (
      <div className="bg-forge-surface border border-forge-border rounded-xl p-6 text-center text-sm text-slate-400">
        <p className="font-mono">Specification is currently at proposal baseline (v1.0).</p>
        <p className="text-xs text-slate-500 mt-1">
          When autonomous agents publish subsequent revisions addressing critiques, visual diff comparisons will appear here.
        </p>
      </div>
    );
  }

  // Default to comparing the latest two versions
  const sorted = [...versions].sort((a, b) => a.version_num - b.version_num);
  const [baseVerNum, setBaseVerNum] = useState<number>(sorted[sorted.length - 2].version_num);
  const [targetVerNum, setTargetVerNum] = useState<number>(sorted[sorted.length - 1].version_num);

  const baseVer = sorted.find((v) => v.version_num === baseVerNum) || sorted[0];
  const targetVer = sorted.find((v) => v.version_num === targetVerNum) || sorted[sorted.length - 1];

  const baseDeliverables: string[] = baseVer.spec_payload?.mvp_deliverables || [];
  const targetDeliverables: string[] = targetVer.spec_payload?.mvp_deliverables || [];

  const baseAcceptance: string[] = baseVer.spec_payload?.acceptance_criteria || [];
  const targetAcceptance: string[] = targetVer.spec_payload?.acceptance_criteria || [];

  return (
    <div className="bg-forge-card border border-forge-border rounded-xl overflow-hidden">
      {/* Header with Version Selector */}
      <div className="bg-forge-surface px-5 py-4 border-b border-forge-border flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold text-white tracking-tight">Specification Version Diff</h3>
          <p className="text-xs text-slate-400">Comparing architectural snapshots across agent revisions</p>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono">
          <select
            value={baseVerNum}
            onChange={(e) => setBaseVerNum(Number(e.target.value))}
            className="bg-forge-card border border-forge-border text-slate-300 rounded px-2.5 py-1 focus:outline-none focus:border-forge-amber"
          >
            {sorted.map((v) => (
              <option key={v.version_num} value={v.version_num}>
                v{v.version_num}.0
              </option>
            ))}
          </select>
          <span className="text-slate-500">→</span>
          <select
            value={targetVerNum}
            onChange={(e) => setTargetVerNum(Number(e.target.value))}
            className="bg-forge-card border border-forge-border text-slate-300 rounded px-2.5 py-1 focus:outline-none focus:border-forge-amber"
          >
            {sorted.map((v) => (
              <option key={v.version_num} value={v.version_num}>
                v{v.version_num}.0
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Changelog Citation Banner */}
      <div className="px-5 py-3.5 bg-forge-amber/10 border-b border-forge-amber/20 flex items-start space-x-3">
        <span className="text-forge-amber font-mono font-bold text-xs mt-0.5">CHANGELOG:</span>
        <div className="text-xs text-slate-200">
          <p className="font-medium">{targetVer.changelog_summary}</p>
          {targetVer.triggered_by_comment_ids && targetVer.triggered_by_comment_ids.length > 0 && (
            <p className="text-[11px] font-mono text-forge-amber/90 mt-1">
              Addressed {targetVer.triggered_by_comment_ids.length} human critique(s) in this revision.
            </p>
          )}
        </div>
      </div>

      {/* Deliverables Diff Section */}
      <div className="p-5 space-y-6">
        <div>
          <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 mb-2.5">
            MVP Deliverables Diff
          </h4>
          <div className="space-y-1.5 font-mono text-xs bg-forge-surface/80 p-3.5 rounded-lg border border-forge-border">
            {baseDeliverables.map((item, idx) => {
              const stillExists = targetDeliverables.includes(item);
              if (!stillExists) {
                return (
                  <div key={`del-${idx}`} className="text-rose-400 bg-rose-500/10 px-2 py-1 rounded flex items-start space-x-2">
                    <span className="font-bold select-none">-</span>
                    <span>{item}</span>
                  </div>
                );
              }
              return (
                <div key={`same-${idx}`} className="text-slate-300 px-2 py-1 flex items-start space-x-2">
                  <span className="text-slate-500 select-none"> </span>
                  <span>{item}</span>
                </div>
              );
            })}

            {targetDeliverables.map((item, idx) => {
              const isNew = !baseDeliverables.includes(item);
              if (isNew) {
                return (
                  <div key={`add-${idx}`} className="text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded flex items-start space-x-2">
                    <span className="font-bold select-none">+</span>
                    <span>{item}</span>
                  </div>
                );
              }
              return null;
            })}
          </div>
        </div>

        {/* Acceptance Criteria Diff Section */}
        <div>
          <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 mb-2.5">
            Acceptance Criteria Diff
          </h4>
          <div className="space-y-1.5 font-mono text-xs bg-forge-surface/80 p-3.5 rounded-lg border border-forge-border">
            {baseAcceptance.map((item, idx) => {
              const stillExists = targetAcceptance.includes(item);
              if (!stillExists) {
                return (
                  <div key={`del-ac-${idx}`} className="text-rose-400 bg-rose-500/10 px-2 py-1 rounded flex items-start space-x-2">
                    <span className="font-bold select-none">-</span>
                    <span>{item}</span>
                  </div>
                );
              }
              return (
                <div key={`same-ac-${idx}`} className="text-slate-300 px-2 py-1 flex items-start space-x-2">
                  <span className="text-slate-500 select-none"> </span>
                  <span>{item}</span>
                </div>
              );
            })}

            {targetAcceptance.map((item, idx) => {
              const isNew = !baseAcceptance.includes(item);
              if (isNew) {
                return (
                  <div key={`add-ac-${idx}`} className="text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded flex items-start space-x-2">
                    <span className="font-bold select-none">+</span>
                    <span>{item}</span>
                  </div>
                );
              }
              return null;
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
