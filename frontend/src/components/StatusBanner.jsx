import React from 'react';

export default function StatusBanner({ sites, isVisible, onToggle }) {
  if (!isVisible) return null;

  const getStatusColor = (status) => {
    switch (status) {
      case 'operational':
        return 'bg-green-500';
      case 'recently_resolved':
        return 'bg-lime-500';
      case 'degraded':
        return 'bg-yellow-500';
      case 'incident':
        return 'bg-red-500';
      case 'maintenance':
        return 'bg-blue-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusEmoji = (status) => {
    switch (status) {
      case 'operational':
        return '✓';
      case 'recently_resolved':
        return '🔄';
      case 'degraded':
        return '⚠';
      case 'incident':
        return '✖';
      case 'maintenance':
        return '🔧';
      default:
        return '?';
    }
  };

  // Filter out console-only sites and duplicate the array for seamless loop
  const activeSites = sites.filter(site => !site.console_only);
  const displaySites = [...activeSites, ...activeSites]; // Duplicate for seamless scroll

  return (
    <div className="relative bg-gray-900 text-white overflow-hidden border-b border-gray-700">
      {/* Close button */}
      <button
        onClick={onToggle}
        className="absolute right-2 top-1/2 -translate-y-1/2 z-10 text-gray-400 hover:text-white px-2 py-1 text-xs"
        title="Hide status banner"
      >
        ✕
      </button>

      {/* Scrolling content */}
      <div className="scroll-banner whitespace-nowrap py-2 pr-8">
        {displaySites.map((site, index) => (
          <span key={`${site.site_id}-${index}`} className="inline-flex items-center mx-6">
            <span className={`inline-block w-2 h-2 rounded-full ${getStatusColor(site.status)} mr-2`}></span>
            <span className="text-sm font-medium">{site.display_name}</span>
            <span className="ml-2 text-xs opacity-75">{getStatusEmoji(site.status)}</span>
          </span>
        ))}
      </div>

      <style dangerouslySetInnerHTML={{
        __html: `
          @keyframes scroll-banner {
            0% {
              transform: translateX(0);
            }
            100% {
              transform: translateX(-50%);
            }
          }

          .scroll-banner {
            animation: scroll-banner 60s linear infinite;
          }

          .scroll-banner:hover {
            animation-play-state: paused;
          }
        `
      }} />
    </div>
  );
}
