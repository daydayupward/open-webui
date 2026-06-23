<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import { fade, fly } from 'svelte/transition';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { settings, config } from '$lib/stores';
	import { injectCsp } from '$lib/utils/csp';

	import XMark from '$lib/components/icons/XMark.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';

	const i18n = getContext('i18n');

	/** Svelte action: moves the node to document.body (portal) */
	function portal(node: HTMLElement) {
		document.body.appendChild(node);
		return {
			destroy() {
				if (node.parentNode) {
					node.parentNode.removeChild(node);
				}
			}
		};
	}

	$: if (show) {
		if (typeof document !== 'undefined') {
			document.body.style.overflow = 'hidden';
			document.body.classList.add('citation-drawer-open');
		}
	} else {
		if (typeof document !== 'undefined') {
			document.body.style.overflow = 'unset';
			document.body.classList.remove('citation-drawer-open');
		}
	}

	onDestroy(() => {
		if (typeof document !== 'undefined') {
			document.body.style.overflow = 'unset';
			document.body.classList.remove('citation-drawer-open');
		}
	});

	const CONTENT_PREVIEW_LIMIT = 10000;
	let expandedDocs: Set<number> = new Set();

	export let show = false;
	export let citation;
	export let showPercentage = false;
	export let showRelevance = true;

	let mergedDocuments = [];

	function calculatePercentage(distance: number) {
		if (typeof distance !== 'number') return null;
		if (distance < 0) return 0;
		if (distance > 1) return 100;
		return Math.round(distance * 10000) / 100;
	}

	function getRelevanceColor(percentage: number) {
		if (percentage >= 80)
			return 'bg-green-200 dark:bg-green-800 text-green-800 dark:text-green-200';
		if (percentage >= 60)
			return 'bg-yellow-200 dark:bg-yellow-800 text-yellow-800 dark:text-yellow-200';
		if (percentage >= 40)
			return 'bg-orange-200 dark:bg-orange-800 text-orange-800 dark:text-orange-200';
		return 'bg-red-200 dark:bg-red-800 text-red-800 dark:text-red-200';
	}

	$: if (citation) {
		expandedDocs = new Set();
		const seenContent = new Set();
		const uniqueDocuments = [];
		citation.document?.forEach((c, i) => {
			const cleanContent = c?.trim() || '';
			if (!seenContent.has(cleanContent)) {
				seenContent.add(cleanContent);
				uniqueDocuments.push({
					source: citation.source,
					document: c,
					metadata: citation.metadata?.[i],
					distance: citation.distances?.[i]
				});
			}
		});
		mergedDocuments = uniqueDocuments;
		if (mergedDocuments.every((doc) => doc.distance !== undefined)) {
			mergedDocuments = mergedDocuments.sort(
				(a, b) => (b.distance ?? Infinity) - (a.distance ?? Infinity)
			);
		}
	}

	const decodeString = (str: string) => {
		try {
			return decodeURIComponent(str);
		} catch {
			return str;
		}
	};

	const getTextFragmentUrl = (doc: any): string | null => {
		const { metadata, source, document: content } = doc ?? {};
		const { file_id, page } = metadata ?? {};
		const sourceUrl = source?.url;

		const baseUrl = file_id
			? `${WEBUI_API_BASE_URL}/files/${file_id}/content${page !== undefined ? `#page=${page + 1}` : ''}`
			: sourceUrl?.includes('http')
				? sourceUrl
				: null;

		if (!baseUrl || !content) return baseUrl;

		// Extract first and last words for text fragment, filtering out URLs and emojis
		const words = content
			.trim()
			.replace(/\s+/g, ' ')
			.split(' ')
			.filter((w: string) => w.length > 0 && !/https?:\/\/|[\u{1F300}-\u{1F9FF}]/u.test(w));

		if (words.length === 0) return baseUrl;

		const clean = (w: string) => w.replace(/[^\w]/g, '');
		const first = clean(words[0]);
		const last = clean(words.at(-1));
		const fragment = words.length === 1 ? first : `${first},${last}`;

		return fragment ? `${baseUrl}#:~:text=${fragment}` : baseUrl;
	};
</script>

{#if show}
	<!-- Overlay Backdrop -->
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		use:portal
		class="fixed inset-0 bg-transparent z-[9998] transition-opacity"
		transition:fade={{ duration: 150 }}
		on:click={() => {
			show = false;
		}}
	></div>

	<!-- Drawer panel -->
	<div
		use:portal
		class="fixed right-0 top-0 h-full w-full max-w-[480px] sm:max-w-[540px] shadow-2xl bg-white dark:bg-gray-900 border-l border-gray-150 dark:border-gray-800 z-[9999] flex flex-col transition-all text-gray-900 dark:text-gray-100"
		transition:fly={{ x: 500, duration: 250 }}
	>
		<!-- Header -->
		<div class="flex justify-between items-center px-5 py-4 border-b border-gray-100 dark:border-gray-800">
			<div class="text-base font-semibold truncate grow flex items-center pr-2">
				{#if citation?.source?.name}
					{@const document = mergedDocuments?.[0]}
					{#if document?.metadata?.file_id || document.source?.url?.includes('http')}
						<Tooltip
							className="w-fit"
							content={document.source?.url?.includes('http')
								? $i18n.t('Open link')
								: $i18n.t('Open file')}
							placement="bottom-start"
							tippyOptions={{ duration: [500, 0] }}
						>
							<a
								class="hover:text-blue-500 dark:hover:text-blue-400 hover:underline grow line-clamp-1 text-sm md:text-base text-left font-semibold"
								href={document?.metadata?.file_id
									? `${WEBUI_API_BASE_URL}/files/${document?.metadata?.file_id}/content${document?.metadata?.page !== undefined ? `#page=${document.metadata.page + 1}` : ''}`
									: document.source?.url?.includes('http')
										? document.source.url
										: `#`}
								target="_blank"
							>
								{decodeString(citation?.source?.name)}
							</a>
						</Tooltip>
					{:else}
						<span class="text-sm md:text-base truncate text-left">{decodeString(citation?.source?.name)}</span>
					{/if}
				{:else}
					<span class="text-sm md:text-base">{$i18n.t('Citation')}</span>
				{/if}
			</div>
			<button
				class="p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400 transition cursor-pointer"
				aria-label={$i18n.t('Close citation drawer')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className="size-5" />
			</button>
		</div>

		<!-- Body -->
		<div class="flex-1 overflow-y-auto p-5 scrollbar-thin flex flex-col gap-4">
			{#each mergedDocuments as document, documentIdx}
				<div class="flex flex-col w-full gap-3 border-b border-gray-100 dark:border-gray-800 last:border-b-0 pb-4 last:pb-0">
					{#if document.metadata?.parameters}
						<div>
							<div class="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 mb-1">
								{$i18n.t('Parameters')}
							</div>
							<Textarea readonly value={JSON.stringify(document.metadata.parameters, null, 2)}
							></Textarea>
						</div>
					{/if}

					<div>
						<div class="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400 flex items-center gap-2 w-fit mb-2">
							{#if document.source?.url?.includes('http')}
								{@const snippetUrl = getTextFragmentUrl(document)}
								{#if snippetUrl}
									<a
										href={snippetUrl}
										target="_blank"
										class="underline hover:text-blue-500 dark:hover:text-blue-400"
										>{$i18n.t('Content')}</a
									>
								{:else}
									{$i18n.t('Content')}
								{/if}
							{:else}
								{$i18n.t('Content')}
							{/if}

							{#if showRelevance && document.distance !== undefined}
								<Tooltip
									className="w-fit"
									content={$i18n.t('Relevance')}
									placement="top-start"
									tippyOptions={{ duration: [500, 0] }}
								>
									<div class="text-xs dark:text-gray-400 flex items-center gap-2 w-fit">
										{#if showPercentage}
											{@const percentage = calculatePercentage(document.distance)}

											{#if typeof percentage === 'number'}
												<span
													class={`px-1 rounded-sm font-medium ${getRelevanceColor(percentage)}`}
												>
													{percentage.toFixed(2)}%
												</span>
											{/if}
										{:else if typeof document?.distance === 'number'}
											<span class="text-gray-500 dark:text-gray-500">
												({(document?.distance ?? 0).toFixed(4)})
											</span>
										{/if}
									</div>
								</Tooltip>
							{/if}

							{#if Number.isInteger(document?.metadata?.page)}
								<span class="text-xs text-gray-500 dark:text-gray-400">
									({$i18n.t('page')} {document.metadata.page + 1})
								</span>
							{/if}
						</div>

						{#if document.metadata?.html}
							<iframe
								class="w-full border border-gray-200 dark:border-gray-800 h-96 rounded-lg"
								sandbox="allow-scripts allow-forms{($settings?.iframeSandboxAllowSameOrigin ??
								false)
									? ' allow-same-origin'
									: ''}"
								srcdoc={injectCsp(document.document, $config?.ui?.iframe_csp ?? '')}
								title={$i18n.t('Content')}
							></iframe>
						{:else}
							{@const rawContent = document.document.trim().replace(/\n\n+/g, '\n\n')}
							{@const isTruncated =
								($settings?.renderMarkdownInPreviews ?? true) &&
								rawContent.length > CONTENT_PREVIEW_LIMIT &&
								!expandedDocs.has(documentIdx)}
							{#if $settings?.renderMarkdownInPreviews ?? true}
								<div class="text-sm prose dark:prose-invert markdown-prose-sm min-w-full max-w-full bg-gray-50 dark:bg-gray-850/50 p-4 rounded-xl border border-gray-100 dark:border-gray-800/80 shadow-xs text-left">
									<Markdown
										content={isTruncated
											? rawContent.slice(0, CONTENT_PREVIEW_LIMIT)
											: rawContent}
										id="citation-{documentIdx}"
									/>
								</div>
								{#if isTruncated}
									<button
										class="mt-2 text-xs text-blue-500 hover:text-blue-600 dark:hover:text-blue-400 font-medium transition cursor-pointer"
										on:click={() => {
											expandedDocs.add(documentIdx);
											expandedDocs = expandedDocs;
										}}
									>
										{$i18n.t('Show all ({{COUNT}} characters)', {
											COUNT: rawContent.length.toLocaleString()
										})}
									</button>
								{/if}
							{:else}
								<pre class="text-sm dark:text-gray-400 bg-gray-50 dark:bg-gray-850/50 p-4 rounded-xl border border-gray-100 dark:border-gray-800 overflow-x-auto whitespace-pre-line font-mono text-left">{rawContent}</pre>
							{/if}
						{/if}
					</div>
				</div>
			{/each}
		</div>
	</div>
{/if}

<style>
	@media (min-width: 640px) {
		:global(body.citation-drawer-open .app) {
			padding-right: 540px;
		}
		:global(.app) {
			transition: padding-right 0.25s cubic-bezier(0.4, 0, 0.2, 1);
		}
	}
</style>
