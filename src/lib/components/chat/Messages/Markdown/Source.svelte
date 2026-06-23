<script lang="ts">
	import { getContext } from 'svelte';
	import { decodeString } from '$lib/utils';

	const i18n = getContext('i18n');

	export let id;

	export let title: string = 'N/A';
	export let index: number | string = '';

	export let onClick: Function = () => {};

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
</script>

{#if title !== 'N/A'}
	<button
		aria-label={$i18n.t('View source: {{title}}', { title: formattedTitle(decodeString(title)) })}
		class="text-[10px] font-semibold text-blue-600 dark:text-blue-400 bg-blue-50/80 hover:bg-blue-100/90 dark:bg-blue-950/30 dark:hover:bg-blue-900/40 border border-blue-100/50 dark:border-blue-900/30 px-1.5 py-0.5 rounded-md transition duration-150 inline-flex items-center align-baseline mx-0.5 cursor-pointer select-none"
		on:click={() => {
			onClick(id);
		}}
	>
		<span class="line-clamp-1">
			[{index || getDisplayTitle(formattedTitle(decodeString(title)))}]
		</span>
	</button>
{/if}
