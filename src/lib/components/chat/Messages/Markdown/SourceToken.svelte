<script lang="ts">
	import { LinkPreview } from 'bits-ui';
	import { decodeString } from '$lib/utils';
	import Source from './Source.svelte';

	export let id;
	export let token;
	export let sourceIds = [];
	export let onClick: Function = () => {};

	let containerElement;
	let openPreview = false;

	// Helper function to return only the domain from a URL
	function getDomain(url: string): string {
		const domain = url.replace('http://', '').replace('https://', '').split(/[/?#]/)[0];

		if (domain.startsWith('www.')) {
			return domain.slice(4);
		}
		return domain;
	}

	// Helper function to check if text is a URL and return the domain
	function formattedTitle(title: string): string {
		if (title.startsWith('http')) {
			return getDomain(title);
		}

		return title;
	}

	const getDisplayTitle = (title: string) => {
		if (!title) return 'N/A';
		if (title.length > 30) {
			return title.slice(0, 15) + '...' + title.slice(-10);
		}
		return title;
	};
</script>

{#if sourceIds && sourceIds.length > 0}
	{#each token?.ids ?? [] as id, idx (idx)}
		{@const identifier = token.citationIdentifiers ? token.citationIdentifiers[idx] : id - 1}
		{@const sourceTitle = sourceIds[id - 1] ?? sourceIds[Math.min(Math.max(0, id - 1), sourceIds.length - 1)]}
		<Source id={identifier} title={sourceTitle} index={id} {onClick} />
	{/each}
{:else}
	<span>{token.raw}</span>
{/if}
