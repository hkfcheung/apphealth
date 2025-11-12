import React from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export default function DownDetectorGraph({ siteId, downdetectorUrl, latestScreenshot, screenshotUploadedAt, onRequestPaste }) {

  if (!downdetectorUrl) {
    return null;
  }

  const screenshotUrl = latestScreenshot
    ? `${API_BASE_URL}/sites/${siteId}/downdetector-screenshot?t=${Date.now()}`
    : null;

  const uploadedAgo = screenshotUploadedAt
    ? new Date(screenshotUploadedAt).toLocaleString()
    : null;

  return (
    <div className="mb-4 p-3 bg-gray-50 rounded-md border border-gray-200">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-semibold text-gray-700">DownDetector Status</h4>
        <a
          href={downdetectorUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 hover:underline transition-colors"
        >
          <span>View live page →</span>
        </a>
      </div>

      {/* Screenshot Display */}
      {screenshotUrl ? (
        <div>
          <img
            src={screenshotUrl}
            alt="DownDetector Screenshot"
            className="w-full rounded border border-gray-300 mb-2"
          />
          <div className="flex items-center justify-between">
            {uploadedAgo && (
              <p className="text-xs text-gray-500">
                Last evidence: {uploadedAgo}
              </p>
            )}
            <button
              onClick={onRequestPaste}
              className="text-xs text-blue-600 hover:text-blue-800 hover:underline"
            >
              📋 Update
            </button>
          </div>
        </div>
      ) : (
        <div>
          <button
            onClick={onRequestPaste}
            className="w-full px-4 py-3 bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium rounded-md transition-colors flex items-center justify-center gap-2"
          >
            <span className="text-lg">📋</span>
            <span>Paste Screenshot</span>
          </button>
          <p className="text-xs text-gray-500 text-center mt-2">
            Take a screenshot of DownDetector, then click to paste
          </p>
        </div>
      )}
    </div>
  );
}
