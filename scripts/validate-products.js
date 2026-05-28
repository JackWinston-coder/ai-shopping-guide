const fs = require('fs')
const path = require('path')

function listJsonFiles(dir) {
  const out = []
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      out.push(...listJsonFiles(full))
    } else if (entry.isFile() && entry.name.endsWith('.json')) {
      out.push(full)
    }
  }
  return out
}

const dataRoot = path.join(process.cwd(), 'data')
const files = listJsonFiles(dataRoot)
const issues = []
const summary = []
const categories = new Set()

for (const file of files) {
  try {
    const raw = fs.readFileSync(file, 'utf8')
    const data = JSON.parse(raw)
    const normalizedImage = path.normalize(path.join(dataRoot, data.image_path))
    const imageExists = fs.existsSync(normalizedImage)
    const skuCount = Array.isArray(data.skus) ? data.skus.length : 0
    const faqCount = data.rag_knowledge?.official_faq?.length ?? 0
    const reviewCount = data.rag_knowledge?.user_reviews?.length ?? 0
    if (data.category) categories.add(data.category)
    summary.push({ file: path.relative(process.cwd(), file), product_id: data.product_id, category: data.category, sub_category: data.sub_category, skuCount, faqCount, reviewCount, imageExists })
    if (!imageExists) {
      issues.push(`${path.relative(process.cwd(), file)}: missing image ${data.image_path}`)
    }
    if (!data.product_id || !data.title || !data.brand || !data.category || !data.sub_category) {
      issues.push(`${path.relative(process.cwd(), file)}: missing required top-level fields`)
    }
    if (!skuCount) {
      issues.push(`${path.relative(process.cwd(), file)}: no skus`)
    }
    if (!faqCount || !reviewCount) {
      issues.push(`${path.relative(process.cwd(), file)}: rag_knowledge incomplete`)
    }
  } catch (err) {
    issues.push(`${path.relative(process.cwd(), file)}: ${err.message}`)
  }
}

console.log(JSON.stringify({ files: files.length, categories: [...categories], summary, issues }, null, 2))
process.exitCode = issues.length ? 1 : 0
