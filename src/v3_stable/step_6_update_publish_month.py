import pymupdf
from sqlalchemy import null
from sqlmodel import select

from src.database import get_db
from src.models import Paper
from src.config import ROOT_PATH
from src.log import logger


def find_month(page: pymupdf.Page) -> str | None:
    """
    从当页中使用相似度匹配找到格式接近 December 2024 的月份表示
    Find month representation similar to 'December 2024' from the page
    """
    # Extract all text from the page
    text = page.get_textpage().extractText()
    
    # Define month names
    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    
    # Look for month patterns in the text
    import re
    for month in months:
        # Pattern: Month YYYY or Month, YYYY
        pattern = f"{month}[,]?\\s+\\d{{4}}"
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    
    # Try abbreviated month names if full names not found
    abbr_months = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]
    
    for month in abbr_months:
        pattern = f"{month}[.]?[,]?\\s+\\d{{4}}"
        match = re.search(pattern, text)
        if match:
            # Convert abbreviated month to full name
            full_month = months[abbr_months.index(month)]
            # Replace abbreviated month with full name
            return match.group(0).replace(month, full_month)
    
    return None


def step_6_update_publish_month():
    with get_db() as session:
        query = select(Paper).where(Paper.publish_month_verified == null())
        papers = session.scalars(query).all()
        for (index, paper) in enumerate(papers[:]):
            logger.info(f"handling [{index} / {len(papers)}] paper: {paper.name}")
            doc = pymupdf.open(ROOT_PATH / paper.name)
            first_page: pymupdf.Page = doc[0]

            publish_month = find_month(first_page)
            logger.info(f"  publish month: {publish_month}")
            paper.publish_month = publish_month
            paper.publish_month_verified = True
            session.add(paper)

        session.commit()


if __name__ == '__main__':
    step_6_update_publish_month()