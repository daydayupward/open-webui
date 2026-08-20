<script lang="ts">
	import { getContext } from 'svelte';
	import { decodeString } from '$lib/utils';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let id;
	export let title: any = 'N/A';
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

	$: displayTitle = typeof title === 'string' ? title : (title?.name || 'N/A');
	$: chunkText = typeof title === 'object' && title?.document?.length > 0 ? title.document[0] : '';

	let showPopover = false;
	let buttonEl: HTMLButtonElement;
	let popoverStyle = '';

	function updatePopoverPosition() {
		if (!buttonEl) return;
		const rect = buttonEl.getBoundingClientRect();
		const popoverWidth = 288; // w-72 = 18rem = 288px
		let left = rect.left + rect.width / 2 - popoverWidth / 2;
		// Clamp to viewport edges
		left = Math.max(8, Math.min(left, window.innerWidth - popoverWidth - 8));
		// Position above the button with small gap
		const top = rect.top - 8;
		popoverStyle = `position:fixed; left:${left}px; top:${top}px; transform:translateY(-100%); z-index:9999;`;
	}

	function handleViewSource(event: MouseEvent) {
		event.stopPropagation();
		showPopover = false;
		onClick(id);
	}

	function handleButtonClick() {
		onClick(id);
	}
</script>

{#if chunkText}
	<!-- Custom popover approach instead of Tippy to avoid DOMPurify stripping onclick -->
	<span class="relative inline-block">
		<button
			id="source-btn-{id}"
			aria-label={$i18n.t('View source: {{title}}', { title: formattedTitle(decodeString(displayTitle)) })}
			class="text-[10px] font-semibold text-blue-600 dark:text-blue-400 bg-blue-50/80 hover:bg-blue-100/90 dark:bg-blue-950/30 dark:hover:bg-blue-900/40 border border-blue-100/50 dark:border-blue-900/30 px-1.5 py-0.5 rounded-md transition duration-150 inline-flex items-center align-baseline mx-0.5 cursor-pointer select-none"
			on:click={handleButtonClick}
			on:mouseenter={() => { updatePopoverPosition(); showPopover = true; }}
			on:mouseleave={() => (showPopover = false)}
			bind:this={buttonEl}
		>
			<span class="line-clamp-1">
				[{index || (displayTitle !== 'N/A' ? getDisplayTitle(formattedTitle(decodeString(displayTitle))) : id)}]
			</span>
		</button>

		{#if showPopover}
			<!-- svelte-ignore a11y-no-static-element-interactions -->
			<div
				class="w-72 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-xl text-sm text-left pointer-events-auto"
				style={popoverStyle}
				on:mouseenter={() => (showPopover = true)}
				on:mouseleave={() => (showPopover = false)}
			>

				<div class="flex flex-col gap-2 p-3">
					<!-- Source name header -->
					<div class="text-xs font-semibold text-gray-500 dark:text-gray-400 truncate">
						{formattedTitle(decodeString(displayTitle))}
					</div>
					<!-- Chunk text preview -->
					<div class="text-xs text-gray-700 dark:text-gray-200 line-clamp-4 leading-relaxed font-normal">
						{chunkText}
					</div>
					<!-- Click hint button -->
					<button
						class="mt-1 text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline text-left cursor-pointer"
						on:click={handleViewSource}
					>
						{$i18n.t('View full document')} &rarr;
					</button>
				</div>
			</div>
		{/if}
	</span>
{:else}
	<button
		id="source-btn-{id}"
		aria-label={$i18n.t('View source: {{title}}', { title: formattedTitle(decodeString(displayTitle)) })}
		class="text-[10px] font-semibold text-blue-600 dark:text-blue-400 bg-blue-50/80 hover:bg-blue-100/90 dark:bg-blue-950/30 dark:hover:bg-blue-900/40 border border-blue-100/50 dark:border-blue-900/30 px-1.5 py-0.5 rounded-md transition duration-150 inline-flex items-center align-baseline mx-0.5 cursor-pointer select-none"
		on:click={handleButtonClick}
		bind:this={buttonEl}
	>
		<span class="line-clamp-1">
			[{index || (displayTitle !== 'N/A' ? getDisplayTitle(formattedTitle(decodeString(displayTitle))) : id)}]
		</span>
	</button>
{/if}
