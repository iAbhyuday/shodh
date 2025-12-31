import React, { useState, useEffect } from 'react';
import { X, Save, RotateCcw, Settings as SettingsIcon } from 'lucide-react';

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
}

const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    // Form State
    const [llmProvider, setLlmProvider] = useState('ollama');
    const [ollamaModel, setOllamaModel] = useState('');
    const [openaiKey, setOpenaiKey] = useState(''); // Only set if changed
    const [openaiModel, setOpenaiModel] = useState('');
    const [geminiKey, setGeminiKey] = useState(''); // Only set if changed
    const [geminiModel, setGeminiModel] = useState('');

    const [embeddingProvider, setEmbeddingProvider] = useState('ollama');

    // Ingestion
    const [doclingVlm, setDoclingVlm] = useState(false);
    const [doclingVlmModel, setDoclingVlmModel] = useState('');
    const [doclingVlmApiUrl, setDoclingVlmApiUrl] = useState('');
    const [doclingVlmApiKey, setDoclingVlmApiKey] = useState('');
    const [doclingVlmPrompt, setDoclingVlmPrompt] = useState('');

    useEffect(() => {
        if (isOpen) {
            fetchSettings();
        }
    }, [isOpen]);

    const fetchSettings = async () => {
        setLoading(true);
        try {
            const res = await fetch('http://localhost:8000/api/settings');
            const data = await res.json();

            setLlmProvider(data.LLM_PROVIDER);
            setOllamaModel(data.OLLAMA_MODEL || '');
            setOpenaiModel(data.OPENAI_MODEL || '');
            setGeminiModel(data.GEMINI_MODEL || '');
            setEmbeddingProvider(data.EMBEDDING_PROVIDER);

            setDoclingVlm(data.DOCLING_ENABLE_VLM);
            setDoclingVlmModel(data.DOCLING_VLM_MODEL || '');
            setDoclingVlmApiUrl(data.DOCLING_VLM_API_URL || '');
            setDoclingVlmPrompt(data.DOCLING_VLM_PROMPT || '');

            // Keys are masked, don't pre-fill unless you want to overwrite
            // We'll leave them empty to indicate "Unchanged"
        } catch (e) {
            console.error("Failed to load settings", e);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            const payload: any = {
                LLM_PROVIDER: llmProvider,
                EMBEDDING_PROVIDER: embeddingProvider,
                DOCLING_ENABLE_VLM: doclingVlm,
                DOCLING_VLM_MODEL: doclingVlmModel,
                DOCLING_VLM_API_URL: doclingVlmApiUrl,
                DOCLING_VLM_PROMPT: doclingVlmPrompt
            };

            if (ollamaModel) payload.OLLAMA_MODEL = ollamaModel;
            if (openaiModel) payload.OPENAI_MODEL = openaiModel;
            if (geminiModel) payload.GEMINI_MODEL = geminiModel;

            // Only send keys if they were typed
            if (openaiKey) payload.OPENAI_API_KEY = openaiKey;
            if (geminiKey) payload.GEMINI_API_KEY = geminiKey;
            if (doclingVlmApiKey) payload.DOCLING_VLM_API_KEY = doclingVlmApiKey;

            const res = await fetch('http://localhost:8000/api/settings/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) throw new Error("Failed to save");

            onClose();
        } catch (e) {
            console.error("Failed to save settings", e);
            alert("Failed to save settings");
        } finally {
            setSaving(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
            <div className="bg-[#121214] border border-white/10 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
                {/* Header */}
                <div className="p-5 border-b border-white/5 flex items-center justify-between bg-[#161618]">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-indigo-500/10 rounded-lg text-indigo-400">
                            <SettingsIcon className="w-5 h-5" />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-white">System Configuration</h2>
                            <p className="text-xs text-gray-400">Adjust AI models and pipeline settings</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-white/5 rounded-lg text-gray-400 hover:text-white transition"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto customized-scrollbar p-6 space-y-8">
                    {loading ? (
                        <div className="text-center py-10 text-gray-500">Loading settings...</div>
                    ) : (
                        <>
                            {/* LLM Section */}
                            <section>
                                <h3 className="text-xs font-bold text-indigo-400 uppercase tracking-widest mb-4">LLM Inference</h3>
                                <div className="space-y-4">
                                    {/* Provider Select */}
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-xs text-gray-400 mb-2 font-medium">Provider</label>
                                            <select
                                                value={llmProvider}
                                                onChange={(e) => setLlmProvider(e.target.value)}
                                                className="w-full bg-[#1a1a1d] border border-white/5 rounded-lg px-3 py-2 text-sm text-white focus:ring-1 focus:ring-indigo-500 outline-none"
                                            >
                                                <option value="ollama">Ollama (Local)</option>
                                                <option value="openai">OpenAI</option>
                                                <option value="gemini">Google Gemini</option>
                                            </select>
                                        </div>
                                        <div>
                                            <label className="block text-xs text-gray-400 mb-2 font-medium">Embedding Provider</label>
                                            <select
                                                value={embeddingProvider}
                                                onChange={(e) => setEmbeddingProvider(e.target.value)}
                                                className="w-full bg-[#1a1a1d] border border-white/5 rounded-lg px-3 py-2 text-sm text-white focus:ring-1 focus:ring-indigo-500 outline-none"
                                            >
                                                <option value="ollama">Ollama (Local)</option>
                                                <option value="openai">OpenAI</option>
                                                <option value="gemini">Google Gemini</option>
                                            </select>
                                        </div>
                                    </div>

                                    {/* Config based on provider */}
                                    <div className="bg-[#1a1a1d] rounded-xl p-4 border border-white/5">
                                        {llmProvider === 'ollama' && (
                                            <div>
                                                <label className="block text-xs text-gray-400 mb-2">Ollama Model Name</label>
                                                <input
                                                    type="text"
                                                    value={ollamaModel}
                                                    onChange={(e) => setOllamaModel(e.target.value)}
                                                    placeholder="e.g. qwen2.5:7b"
                                                    className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2 text-sm text-white outline-none"
                                                />
                                            </div>
                                        )}
                                        {llmProvider === 'openai' && (
                                            <div className="space-y-3">
                                                <div>
                                                    <label className="block text-xs text-gray-400 mb-2">OpenAI Model</label>
                                                    <input
                                                        type="text"
                                                        value={openaiModel}
                                                        onChange={(e) => setOpenaiModel(e.target.value)}
                                                        placeholder="e.g. gpt-4o"
                                                        className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2 text-sm text-white outline-none"
                                                    />
                                                </div>
                                                <div>
                                                    <label className="block text-xs text-gray-400 mb-2">API Key (Leave empty to keep unchanged)</label>
                                                    <input
                                                        type="password"
                                                        value={openaiKey}
                                                        onChange={(e) => setOpenaiKey(e.target.value)}
                                                        placeholder="sk-..."
                                                        className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2 text-sm text-white outline-none"
                                                    />
                                                </div>
                                            </div>
                                        )}
                                        {llmProvider === 'gemini' && (
                                            <div className="space-y-3">
                                                <div>
                                                    <label className="block text-xs text-gray-400 mb-2">Gemini Model</label>
                                                    <input
                                                        type="text"
                                                        value={geminiModel}
                                                        onChange={(e) => setGeminiModel(e.target.value)}
                                                        placeholder="e.g. models/gemini-1.5-flash"
                                                        className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2 text-sm text-white outline-none"
                                                    />
                                                </div>
                                                <div>
                                                    <label className="block text-xs text-gray-400 mb-2">API Key (Leave empty to keep unchanged)</label>
                                                    <input
                                                        type="password"
                                                        value={geminiKey}
                                                        onChange={(e) => setGeminiKey(e.target.value)}
                                                        placeholder="AIza..."
                                                        className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2 text-sm text-white outline-none"
                                                    />
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </section>

                            {/* Ingestion Section */}
                            <section>
                                <h3 className="text-xs font-bold text-indigo-400 uppercase tracking-widest mb-4">Ingestion & Parsing</h3>
                                <div className="bg-[#1a1a1d] rounded-xl p-4 border border-white/5 space-y-4">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <span className="block text-sm font-medium text-white">Enable VLM Parsing</span>
                                            <span className="block text-xs text-gray-400 mt-1">
                                                Use Vision Language Models to parse charts & figures (Slower but detailed).
                                            </span>
                                        </div>
                                        <button
                                            onClick={() => setDoclingVlm(!doclingVlm)}
                                            className={`w-11 h-6 rounded-full transition-colors relative ${doclingVlm ? 'bg-indigo-600' : 'bg-white/10'}`}
                                        >
                                            <div className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-transform ${doclingVlm ? 'left-6' : 'left-1'}`} />
                                        </button>
                                    </div>

                                    {doclingVlm && (
                                        <div className="animate-in fade-in slide-in-from-top-2">
                                            <label className="block text-xs text-gray-400 mb-2">VLM Model Name</label>
                                            <input
                                                type="text"
                                                value={doclingVlmModel}
                                                onChange={(e) => setDoclingVlmModel(e.target.value)}
                                                placeholder="e.g. smolvlm-v1"
                                                className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2 text-sm text-white outline-none focus:ring-1 focus:ring-indigo-500/50"
                                            />

                                            <div className="grid grid-cols-2 gap-4 mt-2">
                                                <div>
                                                    <label className="block text-xs text-gray-400 mb-2">API URL</label>
                                                    <input
                                                        type="text"
                                                        value={doclingVlmApiUrl}
                                                        onChange={(e) => setDoclingVlmApiUrl(e.target.value)}
                                                        placeholder="http://localhost:11434..."
                                                        className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2 text-sm text-white outline-none focus:ring-1 focus:ring-indigo-500/50"
                                                    />
                                                </div>
                                                <div>
                                                    <label className="block text-xs text-gray-400 mb-2">API Key (Optional)</label>
                                                    <input
                                                        type="password"
                                                        value={doclingVlmApiKey}
                                                        onChange={(e) => setDoclingVlmApiKey(e.target.value)}
                                                        placeholder="sk-..."
                                                        className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2 text-sm text-white outline-none focus:ring-1 focus:ring-indigo-500/50"
                                                    />
                                                </div>
                                            </div>

                                            <div className="mt-2">
                                                <label className="block text-xs text-gray-400 mb-2">System Prompt</label>
                                                <input
                                                    type="text"
                                                    value={doclingVlmPrompt}
                                                    onChange={(e) => setDoclingVlmPrompt(e.target.value)}
                                                    placeholder="Convert this page to markdown."
                                                    className="w-full bg-black/20 border border-white/5 rounded-lg px-3 py-2 text-sm text-white outline-none focus:ring-1 focus:ring-indigo-500/50"
                                                />
                                            </div>

                                            <p className="text-[10px] text-gray-500 mt-2">
                                                Note: Changing this will only apply to <strong>newly processed papers</strong>.
                                            </p>
                                        </div>
                                    )}
                                </div>
                            </section>
                        </>
                    )}
                </div>

                {/* Footer */}
                <div className="p-5 border-t border-white/5 bg-[#161618] flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-sm text-gray-400 hover:text-white transition"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-bold rounded-xl transition shadow-lg shadow-indigo-500/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                        {saving ? (
                            <>
                                <RotateCcw className="w-4 h-4 animate-spin" />
                                Saving...
                            </>
                        ) : (
                            <>
                                <Save className="w-4 h-4" />
                                Save Changes
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default SettingsModal;
