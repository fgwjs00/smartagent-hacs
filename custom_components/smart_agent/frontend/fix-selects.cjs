const fs = require('fs');
const files = [
  'src/render/config.js',
  'src/render/main.js',
  'src/render/patrol.js',
  'src/render/backup.js',
  'src/render/habits.js',
  'src/render/corrections.js'
];
files.forEach(f => {
  if (!fs.existsSync(f)) return;
  let c = fs.readFileSync(f, 'utf8');
  let original = c;
  c = c.replace(/<md-outlined-select([^>]*?)\slabel="[^"]*"/g, '<md-outlined-select$1');
  if (original !== c) {
    fs.writeFileSync(f, c);
    console.log('Fixed', f);
  }
});
