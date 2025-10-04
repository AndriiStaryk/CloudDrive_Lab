import React, { useEffect, useRef } from 'react';

export default function ContextMenu({ x, y, items, onClose }) {
    const menuRef = useRef(null);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (menuRef.current && !menuRef.current.contains(event.target)) {
                onClose();
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [onClose]);

    return (
        <div ref={menuRef} className="context-menu" style={{ top: y, left: x }}>
            <ul>
                {items.map(item => (
                    <li key={item.label} onClick={() => { item.action(); onClose(); }}>
                        {item.label}
                    </li>
                ))}
            </ul>
        </div>
    );
}