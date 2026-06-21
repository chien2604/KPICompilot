/**
 * pdf-service/server.js
 *
 * Microservice nhỏ, độc lập với backend Python: nhận HTML (đã render đầy đủ kèm CSS)
 * và trả về PDF bằng Puppeteer (headless Chromium).
 *
 * Backend FastAPI gọi sang đây qua HTTP POST /render khi người dùng bấm "Xuất PDF".
 *
 * Chạy: PORT=4100 npm start
 */
import express from 'express';
import puppeteer from 'puppeteer';

const app = express();
app.use(express.json({ limit: '10mb' }));

const PORT = process.env.PORT || 4100;
const API_KEY = process.env.PDF_SERVICE_API_KEY || null;

let browserPromise = null;

function getBrowser() {
  if (!browserPromise) {
    browserPromise = puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox'],
    });
  }
  return browserPromise;
}

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', service: 'pdf-render-service' });
});

app.post('/render', async (req, res) => {
  if (API_KEY) {
    const provided = req.header('x-api-key');
    if (provided !== API_KEY) {
      return res.status(401).json({ error: 'Unauthorized' });
    }
  }

  const { html, options } = req.body || {};
  if (!html || typeof html !== 'string') {
    return res.status(400).json({ error: 'Thiếu trường "html" (string) trong body' });
  }

  let page;
  try {
    const browser = await getBrowser();
    page = await browser.newPage();
    await page.setContent(html, { waitUntil: 'networkidle0' });

    const pdfBuffer = await page.pdf({
      format: 'A4',
      printBackground: true,
      margin: { top: '12mm', bottom: '12mm', left: '10mm', right: '10mm' },
      ...(options || {}),
    });

    res.set('Content-Type', 'application/pdf');
    res.send(pdfBuffer);
  } catch (error) {
    console.error('[pdf-service] render error:', error);
    res.status(500).json({ error: 'Lỗi render PDF', detail: String(error?.message || error) });
  } finally {
    if (page) {
      await page.close().catch(() => {});
    }
  }
});

app.listen(PORT, () => {
  console.log(`[pdf-service] listening on port ${PORT}`);
});

process.on('SIGINT', async () => {
  if (browserPromise) {
    const browser = await browserPromise;
    await browser.close();
  }
  process.exit(0);
});
