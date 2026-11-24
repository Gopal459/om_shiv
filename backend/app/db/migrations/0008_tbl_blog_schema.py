"""Migration 0008: Create blog cms tables (tbl_blog, tbl_blog_category, tbl_blog_author, tbl_blog_tags, tbl_blog_comments)."""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

requires_session = False


async def upgrade(engine: AsyncEngine) -> None:
    is_sqlite = "sqlite" in str(engine.url)

    async with engine.begin() as conn:
        if is_sqlite:
            # 1. tbl_blog_category
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS tbl_blog_category (
                        blog_category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(264) NOT NULL,
                        slug VARCHAR(264) NOT NULL,
                        meta_title TEXT NULL,
                        meta_keyword TEXT NULL,
                        meta_description TEXT NULL,
                        status INTEGER NOT NULL DEFAULT 1,
                        created_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        modified_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
            )

            # 2. tbl_blog_author
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS tbl_blog_author (
                        author_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        author_name VARCHAR(264) NOT NULL,
                        description TEXT NOT NULL,
                        status INTEGER NOT NULL DEFAULT 0,
                        image VARCHAR(264) NOT NULL,
                        created_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        modified_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
            )

            # 3. tbl_blog_tags
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS tbl_blog_tags (
                        blog_tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(264) NOT NULL UNIQUE,
                        slug VARCHAR(264) NOT NULL UNIQUE,
                        status INTEGER NOT NULL DEFAULT 1,
                        created_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        modified_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
            )

            # 4. tbl_blog
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS tbl_blog (
                        blog_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        blog_category VARCHAR(264) NOT NULL DEFAULT '0',
                        blog_title VARCHAR(264) NOT NULL UNIQUE,
                        blog_title_hindi TEXT NULL,
                        slug VARCHAR(264) NOT NULL UNIQUE,
                        author_name INTEGER NOT NULL DEFAULT 0,
                        blog_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        short_description TEXT NOT NULL,
                        description TEXT NOT NULL,
                        description_hindi TEXT NULL,
                        tags_id VARCHAR(264) NOT NULL DEFAULT '0',
                        image VARCHAR(264) NOT NULL,
                        meta_title TEXT NOT NULL,
                        meta_keyword TEXT NOT NULL,
                        meta_description TEXT NOT NULL,
                        status INTEGER NOT NULL DEFAULT 0,
                        feature INTEGER NOT NULL DEFAULT 0,
                        homepage_status INTEGER NOT NULL DEFAULT 0,
                        total_view INTEGER NOT NULL DEFAULT 0,
                        created_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        modified_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
            )

            # 5. tbl_blog_comments
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS tbl_blog_comments (
                        blog_comm_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        blog_id INTEGER NOT NULL,
                        comment_id INTEGER NOT NULL DEFAULT 0,
                        name VARCHAR(264) NOT NULL,
                        email VARCHAR(264) NOT NULL,
                        comment TEXT NOT NULL,
                        total_like INTEGER NOT NULL DEFAULT 0,
                        status INTEGER NOT NULL DEFAULT 0,
                        comment_by VARCHAR(264) NOT NULL DEFAULT 'user',
                        created_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        modified_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
            )

        else:
            # MySQL / MariaDB syntax
            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS `tbl_blog_category` (
                      `blog_category_id` int(11) NOT NULL AUTO_INCREMENT,
                      `name` varchar(264) NOT NULL,
                      `slug` varchar(264) NOT NULL,
                      `meta_title` text DEFAULT NULL,
                      `meta_keyword` text DEFAULT NULL,
                      `meta_description` text DEFAULT NULL,
                      `status` int(11) NOT NULL DEFAULT 1,
                      `created_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      `modified_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                      PRIMARY KEY (`blog_category_id`),
                      KEY `idx_cat_slug` (`slug`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                    """
                )
            )

            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS `tbl_blog_author` (
                      `author_id` int(11) NOT NULL AUTO_INCREMENT,
                      `author_name` varchar(264) NOT NULL,
                      `description` longtext NOT NULL,
                      `status` int(11) NOT NULL DEFAULT 0,
                      `image` varchar(264) NOT NULL,
                      `created_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      `modified_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                      PRIMARY KEY (`author_id`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                    """
                )
            )

            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS `tbl_blog_tags` (
                      `blog_tag_id` int(11) NOT NULL AUTO_INCREMENT,
                      `name` varchar(264) NOT NULL,
                      `slug` varchar(264) NOT NULL,
                      `status` int(11) NOT NULL DEFAULT 1,
                      `created_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      `modified_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                      PRIMARY KEY (`blog_tag_id`),
                      UNIQUE KEY `name` (`name`),
                      UNIQUE KEY `slug` (`slug`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                    """
                )
            )

            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS `tbl_blog` (
                      `blog_id` int(11) NOT NULL AUTO_INCREMENT,
                      `blog_category` varchar(264) NOT NULL DEFAULT '0',
                      `blog_title` varchar(264) NOT NULL,
                      `blog_title_hindi` text DEFAULT NULL,
                      `slug` varchar(264) NOT NULL,
                      `author_name` int(11) NOT NULL DEFAULT 0,
                      `blog_date` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      `short_description` longtext NOT NULL,
                      `description` longtext NOT NULL,
                      `description_hindi` longtext DEFAULT NULL,
                      `tags_id` varchar(264) NOT NULL DEFAULT '0',
                      `image` varchar(264) NOT NULL,
                      `meta_title` text NOT NULL,
                      `meta_keyword` text NOT NULL,
                      `meta_description` longtext NOT NULL,
                      `status` int(11) NOT NULL DEFAULT 0,
                      `feature` int(11) NOT NULL DEFAULT 0,
                      `homepage_status` int(11) NOT NULL DEFAULT 0,
                      `total_view` int(11) NOT NULL DEFAULT 0,
                      `created_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      `modified_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                      PRIMARY KEY (`blog_id`),
                      UNIQUE KEY `blog_title` (`blog_title`),
                      UNIQUE KEY `slug` (`slug`),
                      KEY `idx_blog_author` (`author_name`),
                      KEY `idx_blog_status` (`status`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                    """
                )
            )

            await conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS `tbl_blog_comments` (
                      `blog_comm_id` int(11) NOT NULL AUTO_INCREMENT,
                      `blog_id` int(11) NOT NULL,
                      `comment_id` int(11) NOT NULL DEFAULT 0,
                      `name` varchar(264) NOT NULL,
                      `email` varchar(264) NOT NULL,
                      `comment` text NOT NULL,
                      `total_like` int(11) NOT NULL DEFAULT 0,
                      `status` int(11) NOT NULL DEFAULT 0,
                      `comment_by` varchar(264) NOT NULL DEFAULT 'user',
                      `created_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      `modified_date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                      PRIMARY KEY (`blog_comm_id`),
                      KEY `idx_blog_id` (`blog_id`),
                      KEY `idx_comment_id` (`comment_id`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                    """
                )
            )
