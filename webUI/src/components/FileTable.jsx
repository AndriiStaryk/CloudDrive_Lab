import React, { useState, useMemo } from 'react';
import { formatDate, formatSize } from '../utils/formatters';
import ContextMenu from './ContextMenu';
import * as api from '../api/apiClient.js';

const columnDefinitions = [
    { key: 'name', label: 'Name' },
    { key: 'size', label: 'Size', format: formatSize, align: 'right' },
    { key: 'uploaded_by', label: 'Uploaded By' },
    { key: 'last_modified_by', label: 'Modified By' },
    { key: 'created_at', label: 'Date Created', format: formatDate },
    { key: 'modified_at', label: 'Date Modified', format: formatDate },
];

export default function FileTable({ files, loading, selectedFile, onFileSelect, onFileDoubleClick, onRename, onDelete, onDownload }) {
    const [sortConfig, setSortConfig] = useState({ key: 'name', direction: 'ascending' });
    const [contextMenu, setContextMenu] = useState(null);
    const [visibleColumns, setVisibleColumns] = useState({
        name: true,
        size: true,
        uploaded_by: true,
        last_modified_by: true,
        created_at: true,
        modified_at: true,
    });

    const activeColumns = useMemo(() => columnDefinitions.filter(c => visibleColumns[c.key]), [visibleColumns]);

    const sortedFiles = useMemo(() => {
        let sortableFiles = [...files];
        if (sortConfig.key) {
            sortableFiles.sort((a, b) => {
                if (a[sortConfig.key] < b[sortConfig.key]) {
                    return sortConfig.direction === 'ascending' ? -1 : 1;
                }
                if (a[sortConfig.key] > b[sortConfig.key]) {
                    return sortConfig.direction === 'ascending' ? 1 : -1;
                }
                return 0;
            });
        }
        return sortableFiles;
    }, [files, sortConfig]);

    const requestSort = (key) => {
        let direction = 'ascending';
        if (sortConfig.key === key && sortConfig.direction === 'ascending') {
            direction = 'descending';
        }
        setSortConfig({ key, direction });
    };

    const getSortIndicator = (key) => {
        if (sortConfig.key !== key) return '↕';
        return sortConfig.direction === 'ascending' ? '↑' : '↓';
    };

    const handleFileContextMenu = (event, file) => {
        event.preventDefault();
        onFileSelect(file);
        const menuItems = [
            { label: 'Rename', action: onRename },
            { label: 'Download', action: onDownload },
            { label: 'Delete', action: onDelete },
        ];
        setContextMenu({ x: event.pageX, y: event.pageY, items: menuItems });
    };

    const handleHeaderContextMenu = (event) => {
        event.preventDefault();
        const toggleColumn = (key) => {
            setVisibleColumns(prev => ({...prev, [key]: !prev[key]}));
        };
        const menuItems = columnDefinitions.map(col => ({
            label: col.label,
            action: () => toggleColumn(col.key),
            type: 'checkbox',
            checked: visibleColumns[col.key],
            disabled: col.key === 'name',
        }));
        setContextMenu({ x: event.pageX, y: event.pageY, items: menuItems });
    };

    const handleDragStart = (e, file) => {
        const url = `${api.apiClient.defaults.baseURL}/files/download/${file.name}`;
        e.dataTransfer.setData('DownloadURL', `${file.name}:${url}`);
        e.dataTransfer.effectAllowed = "copy";
    };

    const handleCloseContextMenu = () => setContextMenu(null);

    return (
        <div className="table-container">
            <table>
                <thead onContextMenu={handleHeaderContextMenu}>
                    <tr>
                        {activeColumns.map(col => (
                           <th key={col.key} onClick={() => requestSort(col.key)} style={{ textAlign: col.align || 'left' }}>
                               {col.label} {getSortIndicator(col.key)}
                           </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {loading ? (
                        <tr><td colSpan={activeColumns.length} style={{textAlign: 'center'}}>Loading files...</td></tr>
                    ) : sortedFiles.length === 0 ? (
                         <tr><td colSpan={activeColumns.length} style={{textAlign: 'center'}}>No files found.</td></tr>
                    ) : (
                        sortedFiles.map(file => (
                            <tr
                                key={file.name}
                                draggable="true"
                                onDragStart={(e) => handleDragStart(e, file)}
                                className={selectedFile?.name === file.name ? 'selected' : ''}
                                onClick={() => onFileSelect(file)}
                                onDoubleClick={() => onFileDoubleClick(file)}
                                onContextMenu={(e) => handleFileContextMenu(e, file)}
                            >
                                {activeColumns.map(col => (
                                    <td key={col.key} style={{ textAlign: col.align || 'left' }}>
                                        {col.format ? col.format(file[col.key]) : file[col.key]}
                                    </td>
                                ))}
                            </tr>
                        ))
                    )}
                </tbody>
            </table>
            {contextMenu && (
                <ContextMenu
                    x={contextMenu.x}
                    y={contextMenu.y}
                    items={contextMenu.items}
                    onClose={handleCloseContextMenu}
                />
            )}
        </div>
    );
}

