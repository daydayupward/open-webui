<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	// State variables
	let activeSubTab = 'ingest'; // 'ingest' | 'catalog' | 'indexes' | 'traces'
	
	// API Base path
	const API_BASE = '/api/v1/retrieval/chip-rag/admin';

	// Ingestion Form State
	let globalConfig = {
		default_header_margin: '50',
		default_footer_margin: '60',
		default_watermark: ''
	};
	let isSavingConfig = false;

	// File Upload State
	let selectedFile: File | null = null;
	let isUploading = false;
	let isPrechecking = false;
	let precheckResult = {
		category: 'PDK',
		vendor: ''
	};
	let uploadForm = {
		category: 'PDK',
		node: '',
		tool: '',
		project_id: '',
		vendor: '',
		header_margin: '',
		footer_margin: '',
		watermark: ''
	};

	// Catalog State
	let documents: any[] = [];
	let isLoadingDocs = false;
	let editingDoc: any = null;
	let filterCategory = 'All';

	// Indexes Versioning State
	let indexesInfo = {
		collections: [] as string[],
		active: {
			PDK: 'pdk_rules',
			EDA: 'eda_manuals',
			Project: 'project_docs'
		}
	};
	let testQuery = '';
	let testCollection = 'pdk_rules';
	let testResults: any[] = [];
	let isTesting = false;
	let isSwitching = false;

	// Observability State
	let traces: any[] = [];
	let isLoadingTraces = false;
	let selectedTrace: any = null;

	onMount(() => {
		loadGlobalConfig();
		loadDocuments();
		loadIndexes();
		loadTraces();
	});

	// --- API CALLS ---
	async function loadGlobalConfig() {
		try {
			const res = await fetch(`${API_BASE}/config`);
			if (res.ok) {
				const data = await res.json();
				globalConfig = { ...globalConfig, ...data };
			}
		} catch (e) {
			console.error(e);
		}
	}

	async function saveGlobalConfig() {
		isSavingConfig = true;
		try {
			const res = await fetch(`${API_BASE}/config`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(globalConfig)
			});
			if (res.ok) {
				toast.success('全局默认配置保存成功！');
			} else {
				toast.error('保存失败');
			}
		} catch (e) {
			toast.error('保存出错: ' + e);
		} finally {
			isSavingConfig = false;
		}
	}

	async function handleFileChange(e: Event) {
		const target = e.target as HTMLInputElement;
		if (target.files && target.files.length > 0) {
			selectedFile = target.files[0];
			// Trigger precheck
			isPrechecking = true;
			try {
				const formData = new FormData();
				formData.append('file', selectedFile);
				const res = await fetch(`${API_BASE}/ingest/precheck`, {
					method: 'POST',
					body: formData
				});
				if (res.ok) {
					const data = await res.json();
					precheckResult = data;
					uploadForm.category = data.category || 'PDK';
					uploadForm.vendor = data.vendor || '';
					toast.info(`预检建议：分类 [${uploadForm.category}]，Vendor [${uploadForm.vendor || '无'}]`);
				}
			} catch (err) {
				console.error('Precheck error', err);
			} finally {
				isPrechecking = false;
			}
		}
	}

	async function handleUpload() {
		if (!selectedFile) {
			toast.error('请选择要导入的文档！');
			return;
		}
		isUploading = true;
		try {
			const formData = new FormData();
			formData.append('file', selectedFile);
			formData.append('category', uploadForm.category);
			if (uploadForm.node) formData.append('node', uploadForm.node);
			if (uploadForm.tool) formData.append('tool', uploadForm.tool);
			if (uploadForm.project_id) formData.append('project_id', uploadForm.project_id);
			if (uploadForm.vendor) formData.append('vendor', uploadForm.vendor);
			if (uploadForm.header_margin) formData.append('header_margin', uploadForm.header_margin);
			if (uploadForm.footer_margin) formData.append('footer_margin', uploadForm.footer_margin);
			if (uploadForm.watermark) formData.append('watermark', uploadForm.watermark);

			const res = await fetch(`${API_BASE}/ingest`, {
				method: 'POST',
				body: formData
			});

			if (res.ok) {
				toast.success('文档上传并摄入任务已在后台启动！');
				selectedFile = null;
				// Reset form
				uploadForm = {
					category: 'PDK',
					node: '',
					tool: '',
					project_id: '',
					vendor: '',
					header_margin: '',
					footer_margin: '',
					watermark: ''
				};
				// Refresh documents list
				setTimeout(loadDocuments, 1500);
			} else {
				const err = await res.text();
				toast.error('上传失败: ' + err);
			}
		} catch (e) {
			toast.error('上传出错: ' + e);
		} finally {
			isUploading = false;
		}
	}

	async function loadDocuments() {
		isLoadingDocs = true;
		try {
			const res = await fetch(`${API_BASE}/documents`);
			if (res.ok) {
				documents = await res.json();
			}
		} catch (e) {
			console.error(e);
		} finally {
			isLoadingDocs = false;
		}
	}

	async function deleteDoc(docId: string) {
		if (!confirm('确定要删除该文档及其对应的所有向量索引分块吗？此操作无法恢复。')) {
			return;
		}
		try {
			const res = await fetch(`${API_BASE}/documents/${docId}`, {
				method: 'DELETE'
			});
			if (res.ok) {
				toast.success('文档删除成功！');
				loadDocuments();
			} else {
				toast.error('删除失败');
			}
		} catch (e) {
			toast.error('删除错误: ' + e);
		}
	}

	async function updateMetadata() {
		if (!editingDoc) return;
		try {
			const res = await fetch(`${API_BASE}/documents/${editingDoc.doc_id}/metadata`, {
				method: 'PUT',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					category: editingDoc.category,
					node: editingDoc.node,
					tool: editingDoc.tool,
					project_id: editingDoc.project_id,
					vendor: editingDoc.vendor
				})
			});
			if (res.ok) {
				toast.success('元数据更新完成，后台正在重构向量索引！');
				editingDoc = null;
				loadDocuments();
			} else {
				toast.error('保存元数据失败');
			}
		} catch (e) {
			toast.error('保存错误: ' + e);
		}
	}

	async function loadIndexes() {
		try {
			const res = await fetch(`${API_BASE}/indexes`);
			if (res.ok) {
				indexesInfo = await res.json();
			}
		} catch (e) {
			console.error(e);
		}
	}

	async function switchCollection(category: string, collection: string) {
		isSwitching = true;
		try {
			const res = await fetch(`${API_BASE}/indexes/switch`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ category, collection })
			});
			if (res.ok) {
				toast.success(`成功切换生产路由，当前 [${category}] 激活索引为: ${collection}`);
				loadIndexes();
			} else {
				toast.error('切换失败');
			}
		} catch (e) {
			toast.error('切换出错: ' + e);
		} finally {
			isSwitching = false;
		}
	}

	async function runSandboxTest() {
		if (!testQuery) {
			toast.error('请输入测试问题！');
			return;
		}
		isTesting = true;
		testResults = [];
		try {
			const res = await fetch(`${API_BASE}/indexes/test`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					query: testQuery,
					collection: testCollection
				})
			});
			if (res.ok) {
				const data = await res.json();
				testResults = data.chunks || [];
				if (testResults.length === 0) {
					toast.info('未召回任何相关分块');
				}
			} else {
				toast.error('检索测试失败');
			}
		} catch (e) {
			toast.error('测试出错: ' + e);
		} finally {
			isTesting = false;
		}
	}

	async function loadTraces() {
		isLoadingTraces = true;
		try {
			const res = await fetch(`${API_BASE}/traces`);
			if (res.ok) {
				traces = await res.json();
			}
		} catch (e) {
			console.error(e);
		} finally {
			isLoadingTraces = false;
		}
	}

	// Categories list helper
	const categories = [
		'PDK', 'StdCell', 'SRAM', 'IP', 'EDA', 
		'Platform_Flow', 'Project_Doc', 'Script', 
		'Literature', 'General'
	];
</script>

<div class="flex flex-col w-full h-full text-gray-900 dark:text-gray-100 bg-transparent">
	<!-- Tab Bar -->
	<div class="flex border-b border-gray-200 dark:border-gray-800 mb-4 gap-4">
		<button
			class="py-2.5 px-4 font-semibold text-sm border-b-2 transition {activeSubTab === 'ingest' ? 'border-blue-600 text-blue-600 dark:text-blue-400' : 'border-transparent text-gray-500 hover:text-gray-700'}"
			on:click={() => activeSubTab = 'ingest'}
		>
			物理清洗与提取 (Ingestion)
		</button>
		<button
			class="py-2.5 px-4 font-semibold text-sm border-b-2 transition {activeSubTab === 'catalog' ? 'border-blue-600 text-blue-600 dark:text-blue-400' : 'border-transparent text-gray-500 hover:text-gray-700'}"
			on:click={() => { activeSubTab = 'catalog'; loadDocuments(); }}
		>
			文档管理目录 (Catalog)
		</button>
		<button
			class="py-2.5 px-4 font-semibold text-sm border-b-2 transition {activeSubTab === 'indexes' ? 'border-blue-600 text-blue-600 dark:text-blue-400' : 'border-transparent text-gray-500 hover:text-gray-700'}"
			on:click={() => { activeSubTab = 'indexes'; loadIndexes(); }}
		>
			多版本索引热切换 (Versioning)
		</button>
		<button
			class="py-2.5 px-4 font-semibold text-sm border-b-2 transition {activeSubTab === 'traces' ? 'border-blue-600 text-blue-600 dark:text-blue-400' : 'border-transparent text-gray-500 hover:text-gray-700'}"
			on:click={() => { activeSubTab = 'traces'; loadTraces(); }}
		>
			链路追踪与可观测 (Traces)
		</button>
	</div>

	<!-- Sub-tab Content Area -->
	<div class="flex-1 overflow-y-auto pr-1">
		{#if activeSubTab === 'ingest'}
			<!-- 1. INGESTION & CLEANING PANEL -->
			<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
				<!-- Global config settings -->
				<div class="p-4 bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-800 rounded-xl">
					<h3 class="font-bold text-base mb-4 flex items-center gap-2">
						<svg class="size-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
						全局解析与清理默认参数
					</h3>
					<div class="space-y-4">
						<div>
							<label class="block text-xs font-semibold text-gray-500 mb-1">默认页眉裁剪高度 (Header Margin px)</label>
							<input
								type="number"
								class="w-full px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg outline-hidden focus:border-blue-500"
								bind:value={globalConfig.default_header_margin}
							/>
						</div>
						<div>
							<label class="block text-xs font-semibold text-gray-500 mb-1">默认页脚裁剪高度 (Footer Margin px)</label>
							<input
								type="number"
								class="w-full px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg outline-hidden focus:border-blue-500"
								bind:value={globalConfig.default_footer_margin}
							/>
						</div>
						<div>
							<label class="block text-xs font-semibold text-gray-500 mb-1">水印清除关键字 (Watermark Pattern)</label>
							<input
								type="text"
								placeholder="e.g. Confidential"
								class="w-full px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg outline-hidden focus:border-blue-500"
								bind:value={globalConfig.default_watermark}
							/>
						</div>
						<button
							class="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm rounded-lg transition disabled:opacity-50"
							on:click={saveGlobalConfig}
							disabled={isSavingConfig}
						>
							{isSavingConfig ? '保存中...' : '保存默认配置'}
						</button>
					</div>
				</div>

				<!-- Single document upload zone -->
				<div class="p-4 bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-800 rounded-xl">
					<h3 class="font-bold text-base mb-4 flex items-center gap-2">
						<svg class="size-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/></svg>
						单文档智能上传与清理覆盖
					</h3>
					
					<!-- File selector drop zone -->
					<div class="border-2 border-dashed border-gray-300 dark:border-gray-700 hover:border-blue-500 rounded-lg p-6 text-center cursor-pointer mb-4 relative transition">
						<input
							type="file"
							class="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
							on:change={handleFileChange}
						/>
						{#if selectedFile}
							<div class="text-blue-600 dark:text-blue-400 font-semibold text-sm">
								已选择: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
							</div>
							<div class="text-xs text-gray-500 mt-1">重新拖拽或点击可更换文件</div>
						{:else}
							<div class="text-gray-500 text-sm">
								拖拽文件到此处，或 <span class="text-blue-600 font-semibold">点击上传</span>
							</div>
							<div class="text-xs text-gray-400 mt-1">支持 PDF, Markdown, Word, Excel, TXT</div>
						{/if}
					</div>

					{#if isPrechecking}
						<div class="flex items-center justify-center gap-2 text-sm text-gray-500 mb-4 py-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg animate-pulse">
							<span>🔍 正在读取文件名和第一页提取信息，推断元数据...</span>
						</div>
					{/if}

					<!-- Metadata Settings -->
					<div class="space-y-3">
						<div class="grid grid-cols-2 gap-3">
							<div>
								<label class="block text-xs font-semibold text-gray-500 mb-1">文档类别 (Category)</label>
								<select
									class="w-full px-2 py-1.5 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg outline-hidden"
									bind:value={uploadForm.category}
								>
									{#each categories as cat}
										<option value={cat}>{cat}</option>
									{/each}
								</select>
							</div>
							<div>
								<label class="block text-xs font-semibold text-gray-500 mb-1">厂商 (Vendor)</label>
								<input
									type="text"
									placeholder="e.g. TSMC"
									class="w-full px-2 py-1.5 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg outline-hidden"
									bind:value={uploadForm.vendor}
								/>
							</div>
						</div>

						<div class="grid grid-cols-3 gap-3">
							<div>
								<label class="block text-xs font-semibold text-gray-500 mb-1">工艺节点 (Node)</label>
								<input
									type="text"
									placeholder="e.g. N5"
									class="w-full px-2 py-1.5 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg outline-hidden"
									bind:value={uploadForm.node}
								/>
							</div>
							<div>
								<label class="block text-xs font-semibold text-gray-500 mb-1">EDA工具 (Tool)</label>
								<input
									type="text"
									placeholder="e.g. Innovus"
									class="w-full px-2 py-1.5 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg outline-hidden"
									bind:value={uploadForm.tool}
								/>
							</div>
							<div>
								<label class="block text-xs font-semibold text-gray-500 mb-1">项目ID (Project ID)</label>
								<input
									type="text"
									placeholder="e.g. Proj_A"
									class="w-full px-2 py-1.5 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg outline-hidden"
									bind:value={uploadForm.project_id}
								/>
							</div>
						</div>

						<!-- Cleaning Overrides (Optional) -->
						<div class="border-t border-gray-200 dark:border-gray-800 pt-3 mt-3">
							<span class="text-xs font-semibold text-gray-400 uppercase tracking-wider block mb-2">针对此文档的清理微调 (留空则使用默认配置)</span>
							<div class="grid grid-cols-3 gap-2">
								<div>
									<label class="block text-[10px] text-gray-500">Header Margin</label>
									<input type="number" class="w-full px-2 py-1 text-xs bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-md" bind:value={uploadForm.header_margin} />
								</div>
								<div>
									<label class="block text-[10px] text-gray-500">Footer Margin</label>
									<input type="number" class="w-full px-2 py-1 text-xs bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-md" bind:value={uploadForm.footer_margin} />
								</div>
								<div>
									<label class="block text-[10px] text-gray-500">Watermark Text</label>
									<input type="text" class="w-full px-2 py-1 text-xs bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-md" bind:value={uploadForm.watermark} />
								</div>
							</div>
						</div>

						<button
							class="w-full py-2.5 mt-4 bg-green-600 hover:bg-green-700 text-white font-bold text-sm rounded-lg transition disabled:opacity-50 flex items-center justify-center gap-2"
							on:click={handleUpload}
							disabled={isUploading || !selectedFile}
						>
							{#if isUploading}
								<span class="size-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
								<span>正在转换并写入索引向量库...</span>
							{:else}
								<span>🚀 开始导入与向量索引重建</span>
							{/if}
						</button>
					</div>
				</div>
			</div>
		{:else if activeSubTab === 'catalog'}
			<!-- 2. METADATA & CATALOG PANEL -->
			<div class="flex flex-col h-full">
				<!-- Filters -->
				<div class="flex gap-2 mb-4 overflow-x-auto pb-1">
					<button
						class="px-3 py-1.5 text-xs font-semibold rounded-full border transition {filterCategory === 'All' ? 'bg-blue-600 text-white border-blue-600' : 'bg-gray-50 dark:bg-gray-850 hover:bg-gray-150 border-gray-300 dark:border-gray-700'}"
						on:click={() => filterCategory = 'All'}
					>
						全部
					</button>
					{#each categories as cat}
						<button
							class="px-3 py-1.5 text-xs font-semibold rounded-full border transition {filterCategory === cat ? 'bg-blue-600 text-white border-blue-600' : 'bg-gray-50 dark:bg-gray-850 hover:bg-gray-150 border-gray-300 dark:border-gray-700'}"
							on:click={() => filterCategory = cat}
						>
							{cat}
						</button>
					{/each}
				</div>

				<!-- Table of Documents -->
				<div class="border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden bg-white dark:bg-gray-900/30">
					{#if isLoadingDocs}
						<div class="p-8 text-center text-gray-500 animate-pulse">正在获取已入库文档目录列表...</div>
					{:else}
						<table class="w-full border-collapse text-left text-sm">
							<thead>
								<tr class="bg-gray-50 dark:bg-gray-950/60 border-b border-gray-200 dark:border-gray-800 text-gray-500 font-semibold text-xs">
									<th class="p-3">文件名</th>
									<th class="p-3">分类</th>
									<th class="p-3">厂商 (Vendor)</th>
									<th class="p-3">节点 (Node)</th>
									<th class="p-3">工具 (Tool)</th>
									<th class="p-3">项目 (Project)</th>
									<th class="p-3 text-center">状态</th>
									<th class="p-3 text-right">操作</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-gray-100 dark:divide-gray-800">
								{#each documents.filter(d => filterCategory === 'All' || d.category === filterCategory) as doc}
									<tr class="hover:bg-gray-50/50 dark:hover:bg-gray-800/30">
										<td class="p-3 font-medium max-w-[200px] truncate">{doc.filename}</td>
										<td class="p-3"><span class="px-2 py-0.5 text-[11px] font-semibold bg-gray-100 dark:bg-gray-800 rounded-full">{doc.category}</span></td>
										<td class="p-3 text-gray-500">{doc.vendor || '-'}</td>
										<td class="p-3 text-gray-500">{doc.node || '-'}</td>
										<td class="p-3 text-gray-500">{doc.tool || '-'}</td>
										<td class="p-3 text-gray-500">{doc.project_id || '-'}</td>
										<td class="p-3 text-center">
											{#if doc.status === 'success'}
												<span class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold bg-green-100 dark:bg-green-950/60 text-green-700 dark:text-green-400 rounded-full">✓ 成功</span>
											{:else if doc.status === 'failed'}
												<span class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold bg-red-100 dark:bg-red-950/60 text-red-700 dark:text-red-400 rounded-full cursor-help" title={doc.error_message}>✗ 失败</span>
											{:else}
												<span class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-semibold bg-blue-100 dark:bg-blue-950/60 text-blue-700 dark:text-blue-400 rounded-full animate-pulse">● 解析中</span>
											{/if}
										</td>
										<td class="p-3 text-right flex justify-end gap-2">
											<button
												class="p-1 hover:text-blue-600 rounded-md transition"
												title="修改元数据属性"
												on:click={() => editingDoc = { ...doc }}
											>
												✏️
											</button>
											<button
												class="p-1 hover:text-red-600 rounded-md transition"
												title="删除文档与索引"
												on:click={() => deleteDoc(doc.doc_id)}
											>
												🗑️
											</button>
										</td>
									</tr>
								{/each}
								{#if documents.length === 0}
									<tr>
										<td colspan="8" class="p-8 text-center text-gray-400">目前没有任何入库文档记录，请切换至 [物理清洗与提取] 进行导入。</td>
									</tr>
								{/if}
							</tbody>
						</table>
					{/if}
				</div>
			</div>

			<!-- Editing Metadata Modal -->
			{#if editingDoc}
				<div class="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center z-50 p-4">
					<div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 w-full max-w-md rounded-2xl p-6 shadow-2xl">
						<h3 class="font-bold text-lg mb-4 text-gray-900 dark:text-white">修改文档元数据属性</h3>
						<div class="space-y-4">
							<div>
								<label class="block text-xs font-semibold text-gray-500 mb-1">文件名</label>
								<input type="text" class="w-full px-3 py-2 text-sm bg-gray-100 dark:bg-gray-800/60 border border-transparent rounded-lg" disabled value={editingDoc.filename} />
							</div>
							<div class="grid grid-cols-2 gap-3">
								<div>
									<label class="block text-xs font-semibold text-gray-500 mb-1">文档分类 (Category)</label>
									<select
										class="w-full px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg outline-hidden"
										bind:value={editingDoc.category}
									>
										{#each categories as cat}
											<option value={cat}>{cat}</option>
										{/each}
									</select>
								</div>
								<div>
									<label class="block text-xs font-semibold text-gray-500 mb-1">厂商 (Vendor)</label>
									<input type="text" class="w-full px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg" bind:value={editingDoc.vendor} />
								</div>
							</div>
							<div class="grid grid-cols-3 gap-3">
								<div>
									<label class="block text-xs font-semibold text-gray-500 mb-1">工艺节点 (Node)</label>
									<input type="text" class="w-full px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg" bind:value={editingDoc.node} />
								</div>
								<div>
									<label class="block text-xs font-semibold text-gray-500 mb-1">EDA工具 (Tool)</label>
									<input type="text" class="w-full px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg" bind:value={editingDoc.tool} />
								</div>
								<div>
									<label class="block text-xs font-semibold text-gray-500 mb-1">项目 ID</label>
									<input type="text" class="w-full px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg" bind:value={editingDoc.project_id} />
								</div>
							</div>

							<div class="flex gap-3 mt-6">
								<button
									class="flex-1 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 font-semibold text-sm rounded-lg transition"
									on:click={() => editingDoc = null}
								>
									取消
								</button>
								<button
									class="flex-1 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm rounded-lg transition"
									on:click={updateMetadata}
								>
									保存并后台重构向量库
								</button>
							</div>
						</div>
					</div>
				</div>
			{/if}
		{:else if activeSubTab === 'indexes'}
			<!-- 3. INDEX & VERSIONING PANEL -->
			<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
				<!-- Multi-version list & Hot-swapping -->
				<div class="lg:col-span-1 p-4 bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-800 rounded-xl">
					<h3 class="font-bold text-base mb-4 flex items-center gap-2">
						<svg class="size-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"/></svg>
						多版本索引与热切换控制
					</h3>
					
					<div class="space-y-6">
						<!-- PDK Collection -->
						<div class="p-3 bg-white dark:bg-gray-800/40 rounded-lg border border-gray-100 dark:border-gray-800">
							<span class="text-xs font-bold text-blue-600 dark:text-blue-400 block mb-1">PDK/StdCell/SRAM 规则索引</span>
							<div class="text-sm font-semibold mb-2">
								当前激活: <span class="font-mono text-xs px-2 py-0.5 bg-green-50 dark:bg-green-950/60 text-green-700 rounded">{indexesInfo.active.PDK}</span>
							</div>
							<div class="flex gap-2">
								<select id="pdk-select" class="flex-1 px-2 py-1 text-xs bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-md outline-hidden">
									{#each indexesInfo.collections as col}
										<option value={col} selected={col === indexesInfo.active.PDK}>{col}</option>
									{/each}
								</select>
								<button
									class="px-3 py-1 bg-blue-600 text-white font-semibold text-xs rounded-md transition hover:bg-blue-700"
									on:click={() => {
										const el = document.getElementById('pdk-select') as HTMLSelectElement;
										switchCollection('PDK', el.value);
									}}
								>
									热切换
								</button>
							</div>
						</div>

						<!-- EDA Collection -->
						<div class="p-3 bg-white dark:bg-gray-800/40 rounded-lg border border-gray-100 dark:border-gray-800">
							<span class="text-xs font-bold text-purple-600 dark:text-purple-400 block mb-1">EDA 手册索引</span>
							<div class="text-sm font-semibold mb-2">
								当前激活: <span class="font-mono text-xs px-2 py-0.5 bg-green-50 dark:bg-green-950/60 text-green-700 rounded">{indexesInfo.active.EDA}</span>
							</div>
							<div class="flex gap-2">
								<select id="eda-select" class="flex-1 px-2 py-1 text-xs bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-md outline-hidden">
									{#each indexesInfo.collections as col}
										<option value={col} selected={col === indexesInfo.active.EDA}>{col}</option>
									{/each}
								</select>
								<button
									class="px-3 py-1 bg-blue-600 text-white font-semibold text-xs rounded-md transition hover:bg-blue-700"
									on:click={() => {
										const el = document.getElementById('eda-select') as HTMLSelectElement;
										switchCollection('EDA', el.value);
									}}
								>
									热切换
								</button>
							</div>
						</div>

						<!-- Project Collection -->
						<div class="p-3 bg-white dark:bg-gray-800/40 rounded-lg border border-gray-100 dark:border-gray-800">
							<span class="text-xs font-bold text-orange-600 dark:text-orange-400 block mb-1">项目文档与脚本索引</span>
							<div class="text-sm font-semibold mb-2">
								当前激活: <span class="font-mono text-xs px-2 py-0.5 bg-green-50 dark:bg-green-950/60 text-green-700 rounded">{indexesInfo.active.Project}</span>
							</div>
							<div class="flex gap-2">
								<select id="project-select" class="flex-1 px-2 py-1 text-xs bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-md outline-hidden">
									{#each indexesInfo.collections as col}
										<option value={col} selected={col === indexesInfo.active.Project}>{col}</option>
									{/each}
								</select>
								<button
									class="px-3 py-1 bg-blue-600 text-white font-semibold text-xs rounded-md transition hover:bg-blue-700"
									on:click={() => {
										const el = document.getElementById('project-select') as HTMLSelectElement;
										switchCollection('Project', el.value);
									}}
								>
									热切换
								</button>
							</div>
						</div>
					</div>
				</div>

				<!-- Sandbox retrieval sandbox query test -->
				<div class="lg:col-span-2 p-4 bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-800 rounded-xl flex flex-col">
					<h3 class="font-bold text-base mb-4 flex items-center gap-2">
						<svg class="size-4 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"/></svg>
						沙箱检索比对与评估环境
					</h3>

					<div class="flex gap-2 mb-4">
						<select
							class="px-2 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg outline-hidden"
							bind:value={testCollection}
						>
							{#each indexesInfo.collections as col}
								<option value={col}>{col}</option>
							{/each}
						</select>
						<input
							type="text"
							placeholder="输入想要召回测试的问题... (e.g. M1.SP.1 spacing rule)"
							class="flex-1 px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg outline-hidden focus:border-blue-500"
							bind:value={testQuery}
							on:keydown={e => e.key === 'Enter' && runSandboxTest()}
						/>
						<button
							class="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white font-semibold text-sm rounded-lg transition disabled:opacity-50"
							on:click={runSandboxTest}
							disabled={isTesting}
						>
							{isTesting ? '检索中...' : '测试检索'}
						</button>
					</div>

					<div class="flex-1 overflow-y-auto max-h-[400px]">
						{#if isTesting}
							<div class="p-8 text-center text-gray-500 animate-pulse">正在召回与评估相关分块并进行Rerank打分...</div>
						{:else}
							<div class="space-y-3">
								{#each testResults as result, idx}
									<div class="p-3 bg-white dark:bg-gray-800/60 border border-gray-200 dark:border-gray-800/80 rounded-lg">
										<div class="flex justify-between items-center mb-1 text-xs">
											<span class="font-semibold text-gray-400">分块 #{idx + 1}</span>
											<div class="flex gap-2">
												<span class="px-2 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-500 rounded truncate max-w-[150px]">{result.metadata.name || result.metadata.source || 'Unknown'}</span>
												<span class="px-2 py-0.5 bg-yellow-50 dark:bg-yellow-950/60 text-yellow-700 font-bold rounded">得分: {result.score.toFixed(4)}</span>
											</div>
										</div>
										<p class="text-xs leading-relaxed font-mono whitespace-pre-wrap text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-900/60 p-2 rounded border border-gray-100 dark:border-gray-850">{result.page_content}</p>
									</div>
								{/each}
								{#if testResults.length === 0}
									<div class="text-center p-8 text-gray-400 text-sm">沙箱暂无检索数据。输入问题并在指定向量版本中召回结果。</div>
								{/if}
							</div>
						{/if}
					</div>
				</div>
			</div>
		{:else if activeSubTab === 'traces'}
			<!-- 4. OBSERVABILITY & TRACES PANEL -->
			<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
				<!-- Recent Traces Table -->
				<div class="lg:col-span-1 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden bg-white dark:bg-gray-900/30">
					<div class="p-3 bg-gray-50 dark:bg-gray-950/60 border-b border-gray-200 dark:border-gray-800 font-bold text-sm">最近 RAG 查询轨迹</div>
					{#if isLoadingTraces}
						<div class="p-6 text-center text-gray-500 animate-pulse">正在获取观测追踪记录...</div>
					{:else}
						<div class="divide-y divide-gray-150 dark:divide-gray-850 max-h-[450px] overflow-y-auto">
							{#each traces as tr}
								<button
									class="w-full text-left p-3 hover:bg-gray-100/50 dark:hover:bg-gray-850/40 transition block {selectedTrace?.id === tr.id ? 'bg-blue-50/50 dark:bg-blue-950/30' : ''}"
									on:click={() => selectedTrace = tr}
								>
									<div class="flex justify-between items-center text-[10px] text-gray-400 mb-1">
										<span>Trace: {tr.id}</span>
										<span>{new Date(tr.timestamp).toLocaleString()}</span>
									</div>
									<div class="text-sm font-semibold truncate text-gray-900 dark:text-white">{tr.query}</div>
									<div class="text-xs text-gray-500 truncate mt-0.5">重写: {tr.rewritten_query}</div>
								</button>
							{/each}
							{#if traces.length === 0}
								<div class="p-6 text-center text-gray-400 text-xs">暂无观测轨迹记录，在与 RAG 进行聊天交互后将自动记录链路。</div>
							{/if}
						</div>
					{/if}
				</div>

				<!-- Selected Trace Detail -->
				<div class="lg:col-span-2 p-4 bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-800 rounded-xl flex flex-col">
					<h3 class="font-bold text-base mb-4 flex items-center gap-2">
						<svg class="size-4 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
						轨迹明细与重写/召回详情
					</h3>

					{#if selectedTrace}
						<div class="space-y-4 overflow-y-auto max-h-[450px] flex-1">
							<!-- Original vs Rewritten -->
							<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
								<div class="p-3 bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-800">
									<span class="text-[10px] font-bold text-gray-400 uppercase">原始提问</span>
									<p class="text-sm mt-1">{selectedTrace.query}</p>
								</div>
								<div class="p-3 bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-800">
									<span class="text-[10px] font-bold text-blue-500 uppercase">重写后的 Query (Self-RAG Loop)</span>
									<p class="text-sm mt-1">{selectedTrace.rewritten_query}</p>
								</div>
							</div>

							<!-- Retrieved chunks -->
							<div>
								<span class="text-xs font-bold text-gray-400 uppercase tracking-wider block mb-2">被采纳并注入上下文的向量分块 ({selectedTrace.retrieved_chunks.length}个)</span>
								<div class="space-y-3">
									{#each selectedTrace.retrieved_chunks as chunk, idx}
										<div class="p-3 bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-800">
											<div class="flex justify-between items-center text-xs text-gray-400 mb-1">
												<span>分块 #{idx + 1} ({chunk.metadata?.category || 'Unknown'})</span>
												<div class="flex gap-2">
													<span class="truncate max-w-[150px]">{chunk.metadata?.name || 'Unknown'}</span>
													<span class="font-bold text-blue-500">得分: {(chunk.metadata?.relevance_score || 0).toFixed(4)}</span>
												</div>
											</div>
											<p class="text-xs leading-relaxed text-gray-700 dark:text-gray-300 font-mono whitespace-pre-wrap bg-gray-50 dark:bg-gray-900/60 p-2 rounded">{chunk.page_content}</p>
										</div>
									{/each}
								</div>
							</div>

							<!-- LLM Answer -->
							<div class="p-3 bg-blue-50 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900 rounded-lg">
								<span class="text-[10px] font-bold text-blue-600 dark:text-blue-400 uppercase block mb-1">大模型最终回复</span>
								<p class="text-sm leading-relaxed whitespace-pre-wrap text-gray-800 dark:text-gray-200 font-sans">{selectedTrace.answer}</p>
							</div>
						</div>
					{:else}
						<div class="flex-1 flex items-center justify-center text-gray-400 text-sm">
							请在左侧列表中选择一条运行轨迹查看详情。
						</div>
					{/if}
				</div>
			</div>
		{/if}
	</div>
</div>
