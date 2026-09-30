-- MySQL dump 10.13  Distrib 9.1.0, for Win64 (x86_64)
--
-- Host: localhost    Database: fyp_parking
-- ------------------------------------------------------
-- Server version	9.1.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `cache`
--

DROP TABLE IF EXISTS `cache`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cache` (
  `key` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `value` mediumtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `expiration` bigint NOT NULL,
  PRIMARY KEY (`key`),
  KEY `cache_expiration_index` (`expiration`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cache`
--

LOCK TABLES `cache` WRITE;
/*!40000 ALTER TABLE `cache` DISABLE KEYS */;
/*!40000 ALTER TABLE `cache` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `cache_locks`
--

DROP TABLE IF EXISTS `cache_locks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cache_locks` (
  `key` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `owner` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `expiration` bigint NOT NULL,
  PRIMARY KEY (`key`),
  KEY `cache_locks_expiration_index` (`expiration`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cache_locks`
--

LOCK TABLES `cache_locks` WRITE;
/*!40000 ALTER TABLE `cache_locks` DISABLE KEYS */;
/*!40000 ALTER TABLE `cache_locks` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `exit_alerts`
--

DROP TABLE IF EXISTS `exit_alerts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `exit_alerts` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `alert_type` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `license_plate` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `detected_color` varchar(191) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `detected_model` varchar(191) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `expected_color` varchar(191) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `expected_model` varchar(191) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `image_path` varchar(191) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `session_id` bigint unsigned DEFAULT NULL,
  `status` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'PENDING',
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `exit_alerts_session_id_foreign` (`session_id`)
) ENGINE=MyISAM AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `exit_alerts`
--

LOCK TABLES `exit_alerts` WRITE;
/*!40000 ALTER TABLE `exit_alerts` DISABLE KEYS */;
INSERT INTO `exit_alerts` VALUES (1,'model_mismatch','VQM568','Black','toyota','Black','tesla','alerts/1Eq0SZYx9ZcrRvEMpzWhSNJGAClYefuxP0DRqxux.jpg',8,'PENDING','2026-08-18 12:03:06','2026-08-18 12:03:06');
/*!40000 ALTER TABLE `exit_alerts` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `failed_jobs`
--

DROP TABLE IF EXISTS `failed_jobs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `failed_jobs` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `uuid` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `connection` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `queue` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `payload` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `exception` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `failed_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `failed_jobs_uuid_unique` (`uuid`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `failed_jobs`
--

LOCK TABLES `failed_jobs` WRITE;
/*!40000 ALTER TABLE `failed_jobs` DISABLE KEYS */;
/*!40000 ALTER TABLE `failed_jobs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `job_batches`
--

DROP TABLE IF EXISTS `job_batches`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `job_batches` (
  `id` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `total_jobs` int NOT NULL,
  `pending_jobs` int NOT NULL,
  `failed_jobs` int NOT NULL,
  `failed_job_ids` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `options` mediumtext COLLATE utf8mb4_unicode_ci,
  `cancelled_at` int DEFAULT NULL,
  `created_at` int NOT NULL,
  `finished_at` int DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `job_batches`
--

LOCK TABLES `job_batches` WRITE;
/*!40000 ALTER TABLE `job_batches` DISABLE KEYS */;
/*!40000 ALTER TABLE `job_batches` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `jobs`
--

DROP TABLE IF EXISTS `jobs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `jobs` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `queue` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `payload` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `attempts` tinyint unsigned NOT NULL,
  `reserved_at` int unsigned DEFAULT NULL,
  `available_at` int unsigned NOT NULL,
  `created_at` int unsigned NOT NULL,
  PRIMARY KEY (`id`),
  KEY `jobs_queue_index` (`queue`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `jobs`
--

LOCK TABLES `jobs` WRITE;
/*!40000 ALTER TABLE `jobs` DISABLE KEYS */;
/*!40000 ALTER TABLE `jobs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `migrations`
--

DROP TABLE IF EXISTS `migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `migrations` (
  `id` int unsigned NOT NULL AUTO_INCREMENT,
  `migration` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `batch` int NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `migrations`
--

LOCK TABLES `migrations` WRITE;
/*!40000 ALTER TABLE `migrations` DISABLE KEYS */;
INSERT INTO `migrations` VALUES (1,'0001_01_01_000000_create_users_table',1),(2,'0001_01_01_000001_create_cache_table',1),(3,'0001_01_01_000002_create_jobs_table',1),(4,'2026_04_09_072124_create_personal_access_tokens_table',1),(5,'2026_04_09_100000_create_parking_sessions_table',1),(6,'2026_04_09_100001_create_payment_receipts_table',1),(7,'2026_06_28_000001_add_grace_end_time_to_parking_sessions_table',1),(8,'2026_06_28_000002_add_payment_type_to_payment_receipts_table',1),(9,'2026_07_16_165310_create_exit_alerts_table',1),(10,'2026_08_09_143714_add_car_image_path_to_parking_sessions_table',1);
/*!40000 ALTER TABLE `migrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `parking_sessions`
--

DROP TABLE IF EXISTS `parking_sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `parking_sessions` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `license_plate` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `color` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `model` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `car_image_path` varchar(191) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `entry_time` timestamp NOT NULL,
  `exit_time` timestamp NULL DEFAULT NULL,
  `grace_end_time` timestamp NULL DEFAULT NULL,
  `amount_due` decimal(8,2) NOT NULL DEFAULT '0.00',
  `status` enum('ENTER','PAID','COMPLETED') COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `parking_sessions_license_plate_index` (`license_plate`),
  KEY `parking_sessions_status_index` (`status`),
  KEY `parking_sessions_entry_time_index` (`entry_time`)
) ENGINE=MyISAM AUTO_INCREMENT=31 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `parking_sessions`
--

LOCK TABLES `parking_sessions` WRITE;
/*!40000 ALTER TABLE `parking_sessions` DISABLE KEYS */;
INSERT INTO `parking_sessions` VALUES (1,'BDR572','Gray','proton','sessions/IL5AsYl1nYuP2lIv4DpnfQhPTqA2zrSaaihEXmTF.jpg','2026-06-30 07:00:54','2026-06-30 08:47:54','2026-06-30 08:47:54',4.00,'COMPLETED','2026-08-09 22:46:56','2026-08-18 12:00:54'),(4,'WRS8850','Gray','toyota','sessions/kbYHA0zASGJoEFSRX6PthhK1ipXKqKPi94VjZQr2.jpg','2026-07-19 07:00:54','2026-07-19 12:19:54','2026-07-19 12:19:54',12.00,'COMPLETED','2026-08-09 22:52:28','2026-08-18 12:00:54'),(8,'VQM568','Black','tesla','sessions/oPnWXl35kZqLqh5cMPa6CqVhqiKAmjglFaaq3pFe.jpg','2026-08-18 10:00:54',NULL,'2026-08-18 12:17:28',6.00,'PAID','2026-08-09 23:02:18','2026-08-18 12:02:28'),(11,'VPT5051','Black','toyota','sessions/IfREg6uEoWjC2pt1DgKIyd7F5QEolpP5uD5KbR0b.jpg','2026-07-27 10:00:54','2026-07-27 13:12:54','2026-07-27 13:12:54',8.00,'COMPLETED','2026-08-10 07:12:24','2026-08-18 12:00:54'),(12,'VNT2602','Black','proton','sessions/QJR0BrJhArDouqPL9xVX7dz9XYS8OAFLLLK5mml0.jpg','2026-08-16 09:00:54','2026-08-16 13:41:54','2026-08-16 13:41:54',10.00,'COMPLETED','2026-08-10 07:13:22','2026-08-18 12:00:54'),(16,'VJT826','Blue','proton','sessions/SOr7BywEM2XDseRSYsu2YmV1jK9uG91gT7WWLfXv.jpg','2026-08-14 10:00:54','2026-08-14 13:23:54','2026-08-14 13:23:54',8.00,'COMPLETED','2026-08-10 07:24:40','2026-08-18 12:00:54'),(14,'VNM8527','Black','perodua','sessions/s1lP2h6BJHFuORI6wDXZfLdp5PZMY9dcoX3qQylh.jpg','2026-08-18 09:00:54',NULL,'2026-08-18 12:20:04',6.00,'PAID','2026-08-10 07:21:16','2026-08-18 12:05:04'),(19,'VCG3438','Black','honda','sessions/dJEwNd5zwPSFdvNpyhkgxSMAUnL9uxsGhgNJ2cwv.jpg','2026-08-15 07:00:54','2026-08-15 10:27:54','2026-08-15 10:27:54',8.00,'COMPLETED','2026-08-10 07:28:43','2026-08-18 12:00:54'),(22,'BBM9234','Red','toyota','sessions/lonCXFcjkL9FZp2mDv54Ib2NBzERbB0UZxN8xkRs.jpg','2026-08-14 08:00:54','2026-08-14 10:19:54','2026-08-14 10:19:54',6.00,'COMPLETED','2026-08-10 07:31:00','2026-08-18 12:00:54'),(25,'BQN1455','Red','perodua','sessions/LX5jaEAnG7kpvTr59dspVKf9Q7RhI1xipTD8DeHm.jpg','2026-06-16 08:00:54','2026-06-16 12:46:54','2026-06-16 12:46:54',10.00,'COMPLETED','2026-08-10 07:35:06','2026-08-18 12:00:54'),(26,'BQP8708','Black','proton','sessions/WrPLKIWcxJs1x6m5zh1MxJqbjXltdhHZ2vqqduhq.jpg','2026-08-17 06:00:54','2026-08-17 09:33:54','2026-08-17 09:33:54',8.00,'COMPLETED','2026-08-10 07:36:01','2026-08-18 12:00:54'),(27,'AMF9050','White','proton','sessions/H8ERntSiK45mzuxLknop8lUVTebcz2Lv7ZRufDj7.jpg','2026-08-18 09:00:54',NULL,'2026-08-18 12:23:21',8.00,'PAID','2026-08-10 07:36:52','2026-08-18 12:08:21'),(29,'WU8729','Gray','toyota','sessions/Sj44kEc2nUnrGNIKJnOut3dROloIooGPUA11jlpa.jpg','2026-08-18 11:55:54',NULL,NULL,0.00,'ENTER','2026-08-10 07:39:37','2026-08-18 12:00:54');
/*!40000 ALTER TABLE `parking_sessions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `password_reset_tokens`
--

DROP TABLE IF EXISTS `password_reset_tokens`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `password_reset_tokens` (
  `email` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `token` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`email`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `password_reset_tokens`
--

LOCK TABLES `password_reset_tokens` WRITE;
/*!40000 ALTER TABLE `password_reset_tokens` DISABLE KEYS */;
/*!40000 ALTER TABLE `password_reset_tokens` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `payment_receipts`
--

DROP TABLE IF EXISTS `payment_receipts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `payment_receipts` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `receipt_number` varchar(191) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `parking_session_id` bigint unsigned NOT NULL,
  `total_amount` decimal(8,2) NOT NULL,
  `payment_date` timestamp NOT NULL,
  `payment_method` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `payment_type` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'initial',
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `payment_receipts_parking_session_id_foreign` (`parking_session_id`),
  KEY `payment_receipts_payment_date_index` (`payment_date`),
  KEY `payment_receipts_payment_method_index` (`payment_method`)
) ENGINE=MyISAM AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `payment_receipts`
--

LOCK TABLES `payment_receipts` WRITE;
/*!40000 ALTER TABLE `payment_receipts` DISABLE KEYS */;
INSERT INTO `payment_receipts` VALUES (1,'RCP-IRNXPS2U',14,6.00,'2026-08-18 11:35:54','Credit Card','initial','2026-08-18 12:00:54','2026-08-18 12:00:54'),(2,'RCP-6LBDQFBL',19,8.00,'2026-08-15 10:22:54','Touch n Go','initial','2026-08-18 12:00:54','2026-08-18 12:00:54'),(3,'RCP-U1L2SNGX',16,8.00,'2026-08-14 13:18:54','Credit Card','initial','2026-08-18 12:00:54','2026-08-18 12:00:54'),(4,'RCP-BZQ9G7ZL',12,10.00,'2026-08-16 13:36:54','Credit Card','initial','2026-08-18 12:00:54','2026-08-18 12:00:54'),(5,'RCP-THGTSVPT',26,8.00,'2026-08-17 09:28:54','Credit Card','initial','2026-08-18 12:00:54','2026-08-18 12:00:54'),(6,'RCP-DDPXGLIE',22,6.00,'2026-08-14 10:14:54','Touch n Go','initial','2026-08-18 12:00:54','2026-08-18 12:00:54'),(7,'RCP-PZ04YSDS',11,8.00,'2026-07-27 13:07:54','Credit Card','initial','2026-08-18 12:00:54','2026-08-18 12:00:54'),(8,'RCP-RJOV44MZ',4,12.00,'2026-07-19 12:14:54','Credit Card','initial','2026-08-18 12:00:54','2026-08-18 12:00:54'),(9,'RCP-JV4LQW2R',25,10.00,'2026-06-16 12:41:54','Touch n Go','initial','2026-08-18 12:00:54','2026-08-18 12:00:54'),(10,'RCP-NTZLCGAW',1,4.00,'2026-06-30 08:42:54','Credit Card','initial','2026-08-18 12:00:54','2026-08-18 12:00:54'),(11,'RCP-RKGG4SUE',8,6.00,'2026-08-18 12:02:28','Touch n Go','initial','2026-08-18 12:02:28','2026-08-18 12:02:28'),(12,'RCP-GWMV7PLR',14,2.00,'2026-08-18 12:05:04','Credit Card','additional','2026-08-18 12:05:04','2026-08-18 12:05:04'),(13,'RCP-P3JDHW9Q',27,8.00,'2026-08-18 12:08:21','Credit Card','initial','2026-08-18 12:08:21','2026-08-18 12:08:21');
/*!40000 ALTER TABLE `payment_receipts` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `personal_access_tokens`
--

DROP TABLE IF EXISTS `personal_access_tokens`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `personal_access_tokens` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `tokenable_type` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `tokenable_id` bigint unsigned NOT NULL,
  `name` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `token` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `abilities` text COLLATE utf8mb4_unicode_ci,
  `last_used_at` timestamp NULL DEFAULT NULL,
  `expires_at` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `personal_access_tokens_token_unique` (`token`),
  KEY `personal_access_tokens_tokenable_type_tokenable_id_index` (`tokenable_type`,`tokenable_id`),
  KEY `personal_access_tokens_expires_at_index` (`expires_at`)
) ENGINE=MyISAM AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `personal_access_tokens`
--

LOCK TABLES `personal_access_tokens` WRITE;
/*!40000 ALTER TABLE `personal_access_tokens` DISABLE KEYS */;
INSERT INTO `personal_access_tokens` VALUES (1,'App\\Models\\User',1,'auth-token','d30d332ff4a13039a5533f76ed57f0fab2323f0beeeda58130f32a6e6cb8cf46','[\"*\"]','2026-08-17 09:09:59',NULL,'2026-08-09 22:48:18','2026-08-17 09:09:59'),(2,'App\\Models\\User',2,'auth-token','2d0ba8d31becb299aadf1fd701a58b28f2dff83efaf682f1fa44545ed1d903d0','[\"*\"]','2026-08-14 03:21:18',NULL,'2026-08-14 03:20:59','2026-08-14 03:21:18'),(3,'App\\Models\\User',2,'auth-token','ebd186e4304a1ae9f828d31aa56ad3a9576de2505a0d04fdefc2c0719db17355','[\"*\"]','2026-08-14 03:36:28',NULL,'2026-08-14 03:21:27','2026-08-14 03:36:28'),(4,'App\\Models\\User',2,'auth-token','87abb1d836686acf7b22f590358d9427df5ac0a2a46f9c6ee0bb1660f73aaa07','[\"*\"]','2026-08-18 11:49:13',NULL,'2026-08-17 09:13:54','2026-08-18 11:49:13'),(5,'App\\Models\\User',2,'auth-token','e2826909fff72114c8ec11f8d6c6008114317e47b796f853f164ae5595a661b5','[\"*\"]','2026-08-18 12:48:54',NULL,'2026-08-18 11:49:22','2026-08-18 12:48:54');
/*!40000 ALTER TABLE `personal_access_tokens` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `sessions`
--

DROP TABLE IF EXISTS `sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sessions` (
  `id` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_id` bigint unsigned DEFAULT NULL,
  `ip_address` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `user_agent` text COLLATE utf8mb4_unicode_ci,
  `payload` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_activity` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `sessions_user_id_index` (`user_id`),
  KEY `sessions_last_activity_index` (`last_activity`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `sessions`
--

LOCK TABLES `sessions` WRITE;
/*!40000 ALTER TABLE `sessions` DISABLE KEYS */;
/*!40000 ALTER TABLE `sessions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email_verified_at` timestamp NULL DEFAULT NULL,
  `password` varchar(191) COLLATE utf8mb4_unicode_ci NOT NULL,
  `remember_token` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `users_email_unique` (`email`)
) ENGINE=MyISAM AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'Admin','admin@smartpark.com','2026-08-09 22:46:13','$2y$12$DZ/zpkuZ4yuSNTUa6coUY.M.TkiUSjsdqDImrwd6t7LXzwWiNA/e6','zXgByZW1m3','2026-08-09 22:46:14','2026-08-09 22:46:14'),(2,'tgx','tgx@gmail.com',NULL,'$2y$12$zVX0f9HQg/.zJj/SLieEi.cPLjCxJnVNIy2VTNSM.Bov7/H.UfVcG',NULL,'2026-08-14 03:20:59','2026-08-14 03:20:59');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-08-18 20:49:18
