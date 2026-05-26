import asyncio
import os
import re
import aiofiles
from playwright.async_api import async_playwright

BASE_DIR = "szse_new_energy_reports"
os.makedirs(BASE_DIR, exist_ok=True)


def safe_filename(name: str):
    return re.sub(r'[\\/:*?"<>|]', "_", name)


async def download_pdf(url, path, request):
    try:
        resp = await request.get(url, timeout=60000)
        if resp.ok:
            content = await resp.body()
            async with aiofiles.open(path, "wb") as f:
                await f.write(content)
            print(f"⬇️ 下载成功: {path}")
    except Exception as e:
        print(f"❌ 下载失败 {url}: {e}")


async def crawl():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print("🚀 打开深圳交易所公告列表...")

        url = "https://www.szse.cn/disclosure/listed/notice/index.html"
        await page.goto(url, timeout=60000)

        request = context.request  # ✅ 修复点（关键）

        page_index = 1

        while page_index <= 30:
            print(f"\n📄 第 {page_index} 页")

            await page.wait_for_timeout(2000)

            items = await page.query_selector_all("a")

            for item in items:
                try:
                    title = await item.inner_text()
                    href = await item.get_attribute("href")

                    if not title or not href:
                        continue

                    # 关键词过滤
                    if "新能源" in title and "年报" in title:

                        if href.startswith("/"):
                            href = "https://www.szse.cn" + href

                        print(f"📌 命中公告: {title}")

                        detail = await context.new_page()
                        await detail.goto(href, timeout=60000)

                        await detail.wait_for_timeout(2000)

                        pdf_links = await detail.query_selector_all("a")

                        for pdf in pdf_links:
                            pdf_href = await pdf.get_attribute("href")
                            pdf_text = await pdf.inner_text()

                            if pdf_href and ".pdf" in pdf_href.lower():
                                if pdf_href.startswith("/"):
                                    pdf_href = "https://www.szse.cn" + pdf_href

                                company = safe_filename(title[:40])
                                folder = os.path.join(BASE_DIR, company)
                                os.makedirs(folder, exist_ok=True)

                                file_path = os.path.join(folder, pdf_text + ".pdf")

                                await download_pdf(pdf_href, file_path, request)

                        await detail.close()

                except Exception as e:
                    print("⚠️ 解析异常:", e)

            # 翻页
            try:
                next_btn = await page.query_selector("text=下一页")
                if next_btn:
                    await next_btn.click()
                    await page.wait_for_timeout(3000)
                    page_index += 1
                else:
                    print("📌 无下一页")
                    break
            except:
                break

        await browser.close()
        print("\n🎉 完成")


if __name__ == "__main__":
    asyncio.run(crawl())