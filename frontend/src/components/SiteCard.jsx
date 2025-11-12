import React from 'react';
import StatusBadge from './StatusBadge';
import Countdown from './Countdown';
import DownDetectorGraph from './DownDetectorGraph';
import { formatRelativeTime, formatDateTime } from '../utils/helpers';

export default function SiteCard({ site, onPollNow, onViewHistory, onEdit, onDelete, onRequestPaste, onConfigureModules }) {
  const handlePollNow = async (e) => {
    e.stopPropagation();
    if (onPollNow) {
      await onPollNow(site.site_id);
    }
  };

  const handleViewHistory = (e) => {
    e.stopPropagation();
    if (onViewHistory) {
      onViewHistory(site);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 mb-1">
            <a
              href={site.status_page}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-blue-600 transition-colors"
            >
              {site.display_name}
            </a>
          </h3>
          {site.console_only && (
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-200 text-gray-700">
              Console Only
            </span>
          )}
        </div>
        <StatusBadge status={site.status} />
      </div>

      {/* Summary */}
      <p className="text-sm text-gray-600 mb-4 line-clamp-2">
        {site.summary || 'No summary available'}
      </p>

      {/* DownDetector Screenshot Upload */}
      {site.downdetector_url && (
        <DownDetectorGraph
          siteId={site.site_id}
          downdetectorUrl={site.downdetector_url}
          latestScreenshot={site.latest_downdetector_screenshot}
          screenshotUploadedAt={site.downdetector_screenshot_uploaded_at}
          onRequestPaste={onRequestPaste}
        />
      )}

      {/* Error Message */}
      {site.error_message && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-700">
            <span className="font-semibold">Error:</span> {site.error_message}
          </p>
        </div>
      )}

      {/* Metadata */}
      <div className="space-y-2 mb-4 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-500">Last checked:</span>
          <span className="text-gray-900" title={formatDateTime(site.last_checked_at)}>
            {formatRelativeTime(site.last_checked_at)}
          </span>
        </div>

        {!site.console_only && site.next_poll_at && (
          <div className="flex justify-between">
            <span className="text-gray-500">Next poll:</span>
            <Countdown nextPollAt={site.next_poll_at} />
          </div>
        )}

        {site.source_type && (
          <div className="flex justify-between">
            <span className="text-gray-500">Source:</span>
            <span className="text-gray-900 font-mono text-xs uppercase">
              {site.source_type}
            </span>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="pt-4 border-t border-gray-200">
        <div className="flex items-center gap-3 text-sm">
          {!site.console_only && (
            <>
              <button
                onClick={handlePollNow}
                className="text-blue-600 hover:underline"
                aria-label={`Poll ${site.display_name} now`}
              >
                Poll Now
              </button>
              <span className="text-gray-400">·</span>
            </>
          )}
          <button
            onClick={handleViewHistory}
            className="text-blue-600 hover:underline"
            aria-label={`View ${site.display_name} history`}
          >
            History
          </button>
          <span className="text-gray-400">·</span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (onConfigureModules) onConfigureModules(site);
            }}
            className="text-blue-600 hover:underline"
            aria-label={`Configure modules for ${site.display_name}`}
          >
            Modules
          </button>
          <span className="text-gray-400">·</span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (onEdit) onEdit(site);
            }}
            className="text-blue-600 hover:underline"
            aria-label={`Edit ${site.display_name}`}
          >
            Edit
          </button>
          <span className="text-gray-400">·</span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (onDelete) onDelete(site.site_id);
            }}
            className="text-red-600 hover:underline"
            aria-label={`Delete ${site.display_name}`}
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
