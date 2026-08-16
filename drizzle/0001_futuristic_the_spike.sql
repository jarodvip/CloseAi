CREATE TABLE `deal_sessions` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`title` varchar(180) NOT NULL,
	`clientSummary` text NOT NULL,
	`primaryType` varchar(80) NOT NULL,
	`secondaryType` varchar(80),
	`diagnosis` text NOT NULL,
	`playbook` text NOT NULL,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `deal_sessions_id` PRIMARY KEY(`id`)
);
