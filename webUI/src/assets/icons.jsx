import React from 'react';

const iconProps = {
  width: "18",
  height: "18",
  viewBox: "0 0 24 24",
  fill: "currentColor"
};

export const UploadIcon = () => (
  <svg {...iconProps}><path d="M9 16h6v-6h4l-7-7-7 7h4v6zm-4 2h14v2H5v-2z" /></svg>
);
export const DownloadIcon = () => (
  <svg {...iconProps}><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z" /></svg>
);
export const DeleteIcon = () => (
  <svg {...iconProps}><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" /></svg>
);
export const RefreshIcon = () => (
  <svg {...iconProps}><path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z" /></svg>
);