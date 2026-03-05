'use client';

import { useState } from 'react';
import { toast } from 'react-toastify';
import { UserPlus, Settings, Wrench, Check, ChevronRight, ChevronLeft, X } from 'lucide-react';
import Card from '@/components/common/Card';
import { apiFetch } from '@/lib/api-client';

interface AgentData {
    name: string;
    emoji: string;
    role: string;
    level: number;
    workspace: string;
    docker_image: string;
    tools: string[];
}

const steps = [
    { id: 'identity', title: 'Identity', icon: UserPlus },
    { id: 'runtime', title: 'Runtime', icon: Settings },
    { id: 'capabilities', title: 'Capabilities', icon: Wrench },
    { id: 'confirm', title: 'Confirm', icon: Check },
];

export default function AgentBuilderWizard({ onClose, onCreated }: { onClose: () => void, onCreated: () => void }) {
    const [currentStep, setCurrentStep] = useState(0);
    const [data, setData] = useState<AgentData>({
        name: '',
        emoji: '🤖',
        role: '',
        level: 3,
        workspace: '/tmp/workspace',
        docker_image: 'python:3.11-slim',
        tools: ['google_search', 'read_url'],
    });

    const handleNext = () => {
        if (currentStep < steps.length - 1) setCurrentStep(currentStep + 1);
    };

    const handleBack = () => {
        if (currentStep > 0) setCurrentStep(currentStep - 1);
    };

    const handleSubmit = async () => {
        try {
            const res = await apiFetch('/api/agents/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });

            if (res.ok) {
                toast.success(`Agent ${data.name} created!`);
                onCreated();
                onClose();
            } else {
                const err = await res.json();
                toast.error(err.message || 'Failed to create agent');
            }
        } catch (err) {
            toast.error('Network error');
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <Card className="w-full max-w-2xl bg-white dark:bg-gray-800 shadow-2xl">
                <div className="flex items-center justify-between p-6 border-b border-gray-100 dark:border-gray-700">
                    <h2 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                        <UserPlus className="w-5 h-5 text-blue-500" />
                        New Agent Builder
                    </h2>
                    <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Stepper */}
                <div className="flex items-center justify-between px-12 py-6 bg-gray-50/50 dark:bg-gray-900/20">
                    {steps.map((step, idx) => (
                        <div key={step.id} className="flex flex-col items-center gap-2 flex-1 relative">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all z-10 ${idx <= currentStep ? 'bg-blue-600 text-white' : 'bg-gray-200 dark:bg-gray-700 text-gray-500'
                                }`}>
                                {idx < currentStep ? <Check className="w-4 h-4" /> : idx + 1}
                            </div>
                            <span className={`text-[10px] uppercase font-bold tracking-wider ${idx <= currentStep ? 'text-blue-600 dark:text-blue-400' : 'text-gray-400 dark:text-gray-600'
                                }`}>
                                {step.title}
                            </span>
                            {idx < steps.length - 1 && (
                                <div className={`absolute left-1/2 top-4 w-full h-0.5 -z-0 ${idx < currentStep ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'
                                    }`} />
                            )}
                        </div>
                    ))}
                </div>

                <div className="p-8 min-h-[300px]">
                    {currentStep === 0 && (
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">Agent Name (ID)</label>
                                <input
                                    type="text"
                                    placeholder="e.g. researcher-alpha"
                                    className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg"
                                    value={data.name}
                                    onChange={e => setData({ ...data, name: e.target.value.toLowerCase().replace(/[^a-z0-9-_]/g, '') })}
                                />
                            </div>
                            <div className="grid grid-cols-4 gap-4">
                                <div className="col-span-1">
                                    <label className="block text-sm font-medium mb-1">Emoji</label>
                                    <input
                                        type="text"
                                        className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg text-center text-xl"
                                        value={data.emoji}
                                        onChange={e => setData({ ...data, emoji: e.target.value })}
                                    />
                                </div>
                                <div className="col-span-3">
                                    <label className="block text-sm font-medium mb-1">Role / Persona</label>
                                    <input
                                        type="text"
                                        placeholder="e.g. Senior Research Assistant"
                                        className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg"
                                        value={data.role}
                                        onChange={e => setData({ ...data, role: e.target.value })}
                                    />
                                </div>
                            </div>
                        </div>
                    )}

                    {currentStep === 1 && (
                        <div className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium mb-1">Level (1-5)</label>
                                    <input
                                        type="number" min="1" max="5"
                                        className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg"
                                        value={data.level}
                                        onChange={e => setData({ ...data, level: parseInt(e.target.value) })}
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-1">Docker Image</label>
                                    <input
                                        type="text"
                                        className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg"
                                        value={data.docker_image}
                                        onChange={e => setData({ ...data, docker_image: e.target.value })}
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">Workspace Path</label>
                                <input
                                    type="text"
                                    className="w-full px-4 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg"
                                    value={data.workspace}
                                    onChange={e => setData({ ...data, workspace: e.target.value })}
                                />
                            </div>
                        </div>
                    )}

                    {currentStep === 2 && (
                        <div className="space-y-4">
                            <p className="text-sm text-gray-500 mb-2">Select starting tools for this agent:</p>
                            <div className="grid grid-cols-2 gap-2">
                                {['google_search', 'read_url', 'bash', 'file_edit', 'browser', 'python'].map(tool => (
                                    <label key={tool} className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-all ${data.tools.includes(tool) ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800' : 'bg-transparent border-gray-200 dark:border-gray-700'
                                        }`}>
                                        <span className="text-sm font-mono">{tool}</span>
                                        <input
                                            type="checkbox"
                                            className="hidden"
                                            checked={data.tools.includes(tool)}
                                            onChange={e => {
                                                const newTools = e.target.checked
                                                    ? [...data.tools, tool]
                                                    : data.tools.filter(t => t !== tool);
                                                setData({ ...data, tools: newTools });
                                            }}
                                        />
                                        {data.tools.includes(tool) && <Check className="w-4 h-4 text-blue-500" />}
                                    </label>
                                ))}
                            </div>
                        </div>
                    )}

                    {currentStep === 3 && (
                        <div className="bg-gray-50 dark:bg-gray-900 rounded-xl p-6 space-y-4">
                            <div className="flex items-center gap-4">
                                <div className="text-4xl">{data.emoji}</div>
                                <div>
                                    <h4 className="font-bold text-lg">{data.name}</h4>
                                    <p className="text-blue-500 text-sm font-medium">{data.role}</p>
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
                                <div className="text-gray-500">Level:</div> <div>{data.level}</div>
                                <div className="text-gray-500">Image:</div> <div>{data.docker_image}</div>
                                <div className="text-gray-500">Tools:</div> <div>{data.tools.join(', ')}</div>
                            </div>
                        </div>
                    )}
                </div>

                <div className="p-6 border-t border-gray-100 dark:border-gray-700 flex justify-between gap-4">
                    <button
                        onClick={handleBack}
                        disabled={currentStep === 0}
                        className={`flex items-center gap-2 px-6 py-2 rounded-lg text-sm font-medium ${currentStep === 0 ? 'text-gray-300 cursor-not-allowed' : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors'
                            }`}
                    >
                        <ChevronLeft className="w-4 h-4" />
                        Back
                    </button>

                    {currentStep === steps.length - 1 ? (
                        <button
                            onClick={handleSubmit}
                            className="flex items-center gap-2 px-8 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-bold shadow-lg shadow-blue-500/20"
                        >
                            Construct Agent
                        </button>
                    ) : (
                        <button
                            onClick={handleNext}
                            className="flex items-center gap-2 px-8 py-2 bg-gray-900 dark:bg-blue-600 hover:bg-black dark:hover:bg-blue-700 text-white rounded-lg text-sm font-bold transition-all"
                        >
                            Continue
                            <ChevronRight className="w-4 h-4" />
                        </button>
                    )}
                </div>
            </Card>
        </div>
    );
}
