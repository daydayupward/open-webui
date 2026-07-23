const { marked } = require('marked');

const input = `**参考来源**:
- [1] innovusUG.pdf
- [2] DBcom.pdf
`;

const tokens = marked.lexer(input);
console.log(JSON.stringify(tokens, null, 2));
