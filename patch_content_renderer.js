const fs = require('fs');
const path = './src/lib/components/chat/Messages/ContentRenderer.svelte';
let content = fs.readFileSync(path, 'utf8');

const oldFunc = `	const getSourceIds = (sources) => {
		const result = [];
		for (const source of sources ?? []) {
			for (let index = 0; index < (source.document ?? []).length; index++) {
				if (model?.info?.meta?.capabilities?.citations == false) {
					result.push('N/A');
					continue;
				}
				const metadata = source.metadata?.[index];
				const id = metadata?.source ?? 'N/A';
				if (metadata?.name) {
					result.push(metadata.name);
				} else if (id.startsWith('http://') || id.startsWith('https://')) {
					result.push(id);
				} else {
					result.push(source?.source?.name ?? id);
				}
			}
		}
		sourceIds = [...new Set(result)];
	};`;

const newFunc = `	const getSourceIds = (sources) => {
		const acc = [];
		for (const source of sources ?? []) {
			for (let index = 0; index < (source.document ?? []).length; index++) {
				if (model?.info?.meta?.capabilities?.citations == false) {
					acc.push({ name: 'N/A', document: [] });
					continue;
				}
				const metadata = source.metadata?.[index];
				const id = metadata?.source ?? source?.source?.id ?? 'N/A';
				
				let name = metadata?.name;
				if (!name) {
					if (id.startsWith('http://') || id.startsWith('https://')) {
						name = id;
					} else {
						name = source?.source?.name ?? id;
					}
				}

				const existingSource = acc.find((item) => item.id === id);
				if (existingSource) {
					existingSource.document.push(source.document?.[index] ?? '');
				} else {
					acc.push({
						id: id,
						name: name,
						document: [source.document?.[index] ?? '']
					});
				}
			}
		}
		sourceIds = acc;
	};`;

content = content.replace(oldFunc, newFunc);
fs.writeFileSync(path, content);
