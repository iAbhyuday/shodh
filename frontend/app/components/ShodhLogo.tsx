import React from 'react';

export const ShodhLogo = ({ className = "w-6 h-6" }: { className?: string }) => {
    return (
        <div className={`relative group ${className}`}>
            <svg
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                className="w-full h-full transition-all duration-300 ease-out group-hover:drop-shadow-[0_0_8px_rgba(139,92,246,0.6)]"
            >
                <path d="M4 19C4 19 6 21 12 21C18 21 20 19 20 19"
                    stroke="#6366F1" strokeWidth="2" strokeLinecap="round" />
                <path d="M12 3C12 3 8 8 8 12C8 14.2091 9.79086 16 12 16C14.2091 16 16 14.2091 16 12C16 8 12 3 12 3Z"
                    fill="url(#paint0_linear_shodh)" />
                <defs>
                    <linearGradient id="paint0_linear_shodh" x1="12" y1="3" x2="12" y2="16" gradientUnits="userSpaceOnUse">
                        <stop stopColor="#8B5CF6" />
                        <stop offset="1" stopColor="#6366F1" />
                    </linearGradient>
                </defs>
            </svg>
        </div>
    );
};
