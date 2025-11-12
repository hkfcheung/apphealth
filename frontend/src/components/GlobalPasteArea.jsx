import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export default function GlobalPasteArea({ activeService, onClose, onUploadSuccess }) {
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const pasteAreaRef = useRef(null);

  useEffect(() => {
    if (activeService) {
      // Auto-focus the paste area when a service becomes active
      pasteAreaRef.current?.focus();
    }
  }, [activeService]);

  useEffect(() => {
    const handlePaste = async (event) => {
      if (!activeService) return;

      event.preventDefault();
      event.stopPropagation();

      const items = event.clipboardData?.items;
      if (!items) return;

      // Find image in clipboard
      let imageFile = null;
      for (let i = 0; i < items.length; i++) {
        if (items[i].type.startsWith('image/')) {
          imageFile = items[i].getAsFile();
          break;
        }
      }

      if (!imageFile) {
        setUploadError('No image found in clipboard. Take a screenshot first (Cmd+Shift+4 or Windows+Shift+S)');
        return;
      }

      await uploadScreenshot(imageFile);
    };

    document.addEventListener('paste', handlePaste);

    return () => {
      document.removeEventListener('paste', handlePaste);
    };
  }, [activeService]);

  const uploadScreenshot = async (file) => {
    setUploading(true);
    setUploadError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      await axios.post(
        `${API_BASE_URL}/sites/${activeService.site_id}/downdetector-screenshot`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      if (onUploadSuccess) {
        onUploadSuccess();
      }
    } catch (error) {
      console.error('Upload error:', error);
      setUploadError(error.response?.data?.detail || 'Failed to upload screenshot');
    } finally {
      setUploading(false);
    }
  };

  if (!activeService) {
    return null;
  }

  return (
    <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50 w-full max-w-md">
      <div className="bg-white rounded-lg shadow-2xl border-2 border-blue-500 p-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-lg">📋</span>
            <div>
              <h3 className="font-semibold text-sm text-gray-900">Paste Screenshot</h3>
              <p className="text-xs text-gray-600">for {activeService.display_name}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Paste Area */}
        <div
          ref={pasteAreaRef}
          tabIndex={0}
          className={`
            border-2 border-dashed rounded-md p-6 transition-all
            ${uploading ? 'border-gray-300 bg-gray-50 cursor-not-allowed' : 'border-blue-400 bg-blue-50'}
          `}
        >
          {uploading ? (
            <div className="flex flex-col items-center justify-center gap-2">
              <div className="animate-spin rounded-full h-8 w-8 border-3 border-gray-300 border-t-blue-600"></div>
              <p className="text-sm text-gray-600">Uploading...</p>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center gap-2">
              <div className="px-4 py-2 bg-blue-500 text-white text-sm rounded-full animate-pulse">
                Ready! Press Cmd+V / Ctrl+V
              </div>
              <p className="text-xs text-gray-600 text-center mt-2">
                Screenshot is in clipboard? Just paste it anywhere on this page
              </p>
            </div>
          )}
        </div>

        {uploadError && (
          <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
            {uploadError}
          </div>
        )}

        <p className="text-xs text-gray-500 text-center mt-3">
          Close this to paste for a different service
        </p>
      </div>
    </div>
  );
}
