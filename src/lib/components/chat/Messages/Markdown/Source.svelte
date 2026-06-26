<script lang="ts">
	import { getContext } from 'svelte';
	import { decodeString } from '$lib/utils';

	const i18n = getContext('i18n');

	export let id;

	export let title: any = 'N/A';
	export let index: number | string = '';

	export let onClick: Function = () => {};

	import Tooltip from '$lib/components/common/Tooltip.svelte';

	// Helper function to return only the domain from a URL
	function getDomain(url: string): string {
		const domain = url.replace('http://', '').replace('https://', '').split(/[/?#]/)[0];

		if (domain.startsWith('www.')) {
			return domain.slice(4);
		}
		return domain;
	}

	const getDisplayTitle = (title: string) => {
		if (!title) return 'N/A';
		if (title.length > 30) {
			return title.slice(0, 15) + '...' + title.slice(-10);
		}
		return title;
	};

	// Helper function to check if text is a URL and return the domain
	function formattedTitle(title: string): string {
		if (title.startsWith('http')) {
			return getDomain(title);
		}

		return title;
	}

	$: displayTitle = typeof title === 'string' ? title : (title?.name || 'N/A');
	$: chunkText = typeof title === 'object' && title?.document?.length > 0 ? title.document[0] : '';
	
	$: chunkHtml = chunkText ? `
		<div class="flex flex-col gap-2 p-2 max-w-[300px] text-sm text-left">
			<div class="line-clamp-6 text-gray-200 break-words whitespace-pre-wrap">
				${chunkText}
			</div>
			<button class="text-blue-400 hover:text-blue-300 hover:underline text-xs self-end mt-1 cursor-pointer" onclick="document.getElementById('source-btn-${id}').click()">
				${$i18n.t('View Source')}
			</button>
		</div>
	` : '';
</script>

{#if displayTitle !== 'N/A'}
	{#if chunkText}
		<Tooltip content={chunkHtml} allowHTML={true} interactive={true} placement="top" className="w-fit inline-block">
			<button
				id="source-btn-{id}"
				aria-label={$i18n.t('View source: {{title}}', { title: formattedTitle(decodeString(displayTitle)) })}
				class="text-[10px] font-semibold text-blue-600 dark:text-blue-400 bg-blue-50/80 hover:bg-blue-100/90 dark:bg-blue-950/30 dark:hover:bg-blue-900/40 border border-blue-100/50 dark:border-blue-900/30 px-1.5 py-0.5 rounded-md transition duration-150 inline-flex items-center align-baseline mx-0.5 cursor-pointer select-none"
				on:click={() => {
					onClick(id);
				}}
			>
				<span class="line-clamp-1">
					[{index || getDisplayTitle(formattedTitle(decodeString(displayTitle)))}]
				</span>
			</button>
		</Tooltip>
	{:else}
		<button
			id="source-btn-{id}"
			aria-label={$i18n.t('View source: {{title}}', { title: formattedTitle(decodeString(displayTitle)) })}
			class="text-[10px] font-semibold text-blue-600 dark:text-blue-400 bg-blue-50/80 hover:bg-blue-100/90 dark:bg-blue-950/30 dark:hover:bg-blue-900/40 border border-blue-100/50 dark:border-blue-900/30 px-1.5 py-0.5 rounded-md transition duration-150 inline-flex items-center align-baseline mx-0.5 cursor-pointer select-none"
			on:click={() => {
				onClick(id);
			}}
		>
			<span class="line-clamp-1">
				[{index || getDisplayTitle(formattedTitle(decodeString(displayTitle)))}]
			</span>
		</button>
	{/if}
{/if}
