import React from 'react';
import { getStatusColor, getStatusDisplayName } from '../utils/helpers';

export default function StatusBadge({ status }) {
  return (
    <span
      className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(
        status
      )}`}
    >
      {getStatusDisplayName(status)}
    </span>
  );
}
