---
title: "Self-Hosted Quiz & Trivia Platforms: Open Trivia vs Quizmaster vs PHPQuiz 2026"
date: "2026-06-19"
tags: ["quiz", "trivia", "education", "assessment", "self-hosted", "game", "learning"]
draft: false
---

## Why Self-Host a Quiz Platform?

Online quizzes and trivia games have exploded in popularity — from corporate training assessments and classroom exams to pub trivia nights and team-building activities. While platforms like Kahoot and Quizlet dominate the market, they lock your content behind subscriptions, limit customization, and collect data on your participants.

Self-hosting your own quiz platform gives you complete control over branding, question banks, participant data, and pricing. Whether you're an educator building formative assessments, a bar hosting weekly trivia nights, or a company running compliance training, a self-hosted solution costs a fraction of commercial alternatives and keeps your data private.

In this guide, we compare three open-source self-hosted quiz platforms: **Open Trivia Database**, **Quizmaster**, and **phpQuiz**. Each takes a different approach — from a full-featured trivia engine to a lightweight embeddable quiz widget.

## Comparison Table

| Feature | Open Trivia DB | Quizmaster | phpQuiz |
|---------|---------------|------------|---------|
| **Type** | Full platform | Embeddable widget | Standalone app |
| **Stars** | 700+ | 400+ | 300+ |
| **Language** | Node.js/React | JavaScript | PHP |
| **Database** | MongoDB | None (JSON) | MySQL |
| **Question Types** | Multiple choice, TF | Multiple choice | Multiple choice, TF, Fill-in |
| **Multiplayer** | Real-time rooms | No | No |
| **Leaderboard** | Yes | Yes | Yes |
| **Timer Support** | Per-question | Per-quiz | Per-question |
| **API** | REST + WebSocket | Embed script | REST |
| **Docker Support** | Yes | Static files | Yes |
| **Theming** | CSS variables | Full CSS | Template-based |
| **Export Results** | CSV | JSON | CSV, PDF |
| **Best For** | Live trivia events | Blog quizzes | Structured exams |

## 1. Open Trivia Database: Real-Time Multiplayer Trivia

Open Trivia Database (OpenTDB) is a Node.js/React platform designed for live trivia events. It supports real-time multiplayer rooms via WebSockets, making it ideal for pub quizzes, corporate events, and classroom competitions.

### Docker Compose Setup

```yaml
version: "3.8"
services:
  opentdb:
    image: opentdb/opentdb:latest
    container_name: opentdb
    ports:
      - "3000:3000"
    environment:
      - MONGODB_URI=mongodb://mongo:27017/opentdb
      - JWT_SECRET=your-secret-key-change-me
      - SESSION_SECRET=another-secret-key
      - ADMIN_EMAIL=admin@example.com
      - ADMIN_PASSWORD=secure_admin_password
    depends_on:
      - mongo
    restart: unless-stopped

  mongo:
    image: mongo:7
    container_name: opentdb-mongo
    volumes:
      - opentdb_data:/data/db
    restart: unless-stopped

volumes:
  opentdb_data:
```

### Creating a Live Trivia Room

1. Log into the admin panel at `http://your-server:3000/admin`
2. Create a new quiz with questions (supports bulk import via JSON)
3. Generate a room code that participants join
4. Participants visit `http://your-server:3000/join` and enter the code
5. The host controls question pacing — results update in real-time

```javascript
// Example: Bulk import questions via the REST API
const questions = [
  {
    category: "Science",
    question: "What is the chemical symbol for gold?",
    correct_answer: "Au",
    incorrect_answers: ["Ag", "Fe", "Cu"],
    difficulty: "medium"
  },
  {
    category: "History",
    question: "In which year did World War II end?",
    correct_answer: "1945",
    incorrect_answers: ["1944", "1946", "1943"],
    difficulty: "easy"
  }
];

await fetch('http://your-server:3000/api/questions/bulk', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${apiToken}`
  },
  body: JSON.stringify({ questions })
});
```

### Real-Time Architecture

OpenTDB uses Socket.io for real-time communication between the host and participants. When the host advances to the next question, all connected clients receive the question simultaneously. Answers are submitted individually, and the leaderboard updates in real-time as participants respond.

## 2. Quizmaster: Embeddable Quiz Widgets

Quizmaster is a lightweight, dependency-free JavaScript quiz engine that can be embedded in any website. It stores all quiz data in a single JSON file, requires no backend, and can be deployed as static files on any web server or CDN.

### Deployment (Static Files)

```bash
# Clone the repository
git clone https://github.com/nickpack/quizmaster.git
cd quizmaster

# Edit quizzes in quizzes/ directory (JSON format)
# Deploy to any static hosting
rsync -avz ./ user@your-server:/var/www/quizmaster/
```

### Quiz JSON Format

```json
{
  "title": "Web Development Trivia",
  "description": "Test your knowledge of web technologies",
  "timeLimit": 300,
  "questions": [
    {
      "question": "What does CSS stand for?",
      "options": [
        "Cascading Style Sheets",
        "Computer Style System",
        "Creative Style Syntax",
        "Cascading System Styles"
      ],
      "answer": 0
    },
    {
      "question": "Which HTML tag is used for the largest heading?",
      "options": ["<heading>", "<h6>", "<h1>", "<head>"],
      "answer": 2
    }
  ]
}
```

### Embedding in Your Website

```html
<!-- Add the quiz to any page -->
<div id="quiz-container"></div>
<script src="https://quiz.yourdomain.com/quizmaster.js"></script>
<script>
  Quizmaster.init({
    container: '#quiz-container',
    quizUrl: 'https://quiz.yourdomain.com/quizzes/web-dev.json',
    theme: 'dark',
    onComplete: function(results) {
      console.log('Score:', results.score, '/', results.total);
      // Send results to your analytics
      fetch('/api/quiz-results', {
        method: 'POST',
        body: JSON.stringify(results)
      });
    }
  });
</script>
```

This approach is perfect for bloggers who want to add interactive quizzes to articles, educators embedding assessments in course pages, or marketers creating lead-generation quizzes.

### Nginx Configuration for Static Hosting

```nginx
server {
    listen 443 ssl http2;
    server_name quiz.yourdomain.com;

    root /var/www/quizmaster;
    index index.html;

    # Enable CORS for cross-domain embedding
    add_header Access-Control-Allow-Origin *;

    # Cache static assets
    location ~* \.(js|css|json|png|jpg|svg)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    ssl_certificate /etc/letsencrypt/live/quiz.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/quiz.yourdomain.com/privkey.pem;
}
```

## 3. phpQuiz: Traditional Exam-Style Assessments

phpQuiz is a PHP/MySQL-based platform designed for structured assessments — think certification exams, school tests, and compliance training. It supports question banks, randomized question selection, timed exams, and detailed result reporting.

### Docker Compose Setup

```yaml
version: "3.8"
services:
  phpquiz:
    image: phpquiz/phpquiz:latest
    container_name: phpquiz
    ports:
      - "8080:80"
    environment:
      - DB_HOST=db
      - DB_NAME=phpquiz
      - DB_USER=phpquiz
      - DB_PASSWORD=secure_password
      - SITE_URL=https://quiz.yourdomain.com
    volumes:
      - phpquiz_uploads:/var/www/html/uploads
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: mysql:8.0
    container_name: phpquiz-db
    environment:
      - MYSQL_ROOT_PASSWORD=root_password
      - MYSQL_DATABASE=phpquiz
      - MYSQL_USER=phpquiz
      - MYSQL_PASSWORD=secure_password
    volumes:
      - phpquiz_db:/var/lib/mysql
    restart: unless-stopped

volumes:
  phpquiz_uploads:
  phpquiz_db:
```

### Exam Features

- **Question Banks**: Organize questions by topic, difficulty, and tags
- **Randomization**: Draw N questions randomly from a pool for each attempt
- **Time Limits**: Set per-exam or per-question time limits
- **Result Reports**: Export individual and aggregate results as CSV or PDF
- **Access Control**: Password-protect exams or restrict by IP range
- **Grading**: Automatic scoring for multiple choice; manual review for essay questions

## Deployment Security Considerations

When self-hosting quiz platforms that handle participant data, follow these security practices:

1. **Enable HTTPS** — All quiz platforms should run behind TLS. Use Let's Encrypt with Caddy or Certbot+Nginx for automatic certificate management.

2. **Rate limit submissions** — Prevent answer enumeration attacks by rate-limiting POST requests to quiz submission endpoints.

3. **Sanitize user inputs** — If your platform allows user-generated content (custom quiz names, team names), sanitize inputs to prevent XSS attacks.

4. **Regular backups** — Question banks represent significant intellectual investment. Schedule automated database backups.

5. **Access logging** — Monitor access patterns to detect cheating attempts (e.g., rapid submissions, answers matching known patterns).

For broader learning management system comparisons, see our [best self-hosted LMS guide](../best-self-hosted-lms-platforms-moodle-openedx-chamilo-guide-2026/). If you need advanced assessment capabilities beyond quizzes, check our [LMS beyond Moodle comparison](../2026-06-13-self-hosted-lms-beyond-moodle-ilias-sakai-canvas/). For spaced repetition and flashcard-based learning, see our [self-hosted SRS guide](../2026-05-01-anki-sync-server-vs-memo-vs-omniget-self-hosted-spaced-repetition-srs-comparison/).

## Choosing the Right Quiz Platform for Your Use Case

Selecting between Open Trivia Database, Quizmaster, and phpQuiz depends entirely on your specific needs. Here is a decision framework to help you choose.

**Choose Open Trivia Database if** you are hosting live events — pub trivia nights, corporate team-building, classroom competitions, or conference activities. The real-time multiplayer rooms, WebSocket-powered leaderboard updates, and host-controlled question pacing make it the only choice for live, synchronous quiz experiences. The learning curve is higher (MongoDB, Node.js, WebSocket configuration), but the participant experience is unmatched for group events.

**Choose Quizmaster if** you need to embed quizzes in existing web content — blog posts, marketing landing pages, course websites, or onboarding flows. Its zero-backend architecture means you can deploy it alongside any static site or CMS without additional infrastructure. The tradeoff is limited question types (multiple choice only) and no server-side result persistence by default, though you can add your own backend integration via the completion callback.

**Choose phpQuiz if** you are building structured assessments — employee certification exams, school tests, compliance training, or graded coursework. Its question bank system, randomized selection, time-limited exams, and PDF result export make it suitable for formal assessment scenarios where you need audit trails and documented results. The PHP/MySQL stack is easy to deploy on shared hosting, making it accessible for schools and small organizations without dedicated DevOps resources.

For organizations that need both live trivia AND structured assessments, consider running Open Trivia Database for events and phpQuiz for exams — the two platforms complement each other without overlapping functionality. Both can share the same Nginx reverse proxy and PostgreSQL database server if you standardize on compatible database engines.


## FAQ

### Can I import questions from Quizlet or Kahoot into a self-hosted platform?

Most self-hosted platforms support JSON or CSV import. You can export your Quizlet sets as text, format them as JSON matching the platform's schema, and bulk import. Open Trivia Database provides a REST API endpoint specifically for bulk question import. Some community tools also exist to convert Quizlet exports to OpenTDB format.

### How many simultaneous participants can a self-hosted quiz handle?

Open Trivia Database (Node.js + WebSockets) handles 200-500 simultaneous participants on a 2GB VPS. Quizmaster (static files) scales to thousands since there's no server-side processing — all quiz logic runs in the browser. phpQuiz handles 50-100 simultaneous test-takers comfortably on modest hardware.

### Can I use these platforms offline or on a local network?

Yes. All three platforms can run entirely on a local network without internet access. For live events in venues with unreliable internet, deploy the server on a local machine (laptop or Raspberry Pi) and have participants connect via the venue's WiFi. Quizmaster is particularly well-suited for this since it's static files that can be served from any device.

### How do I prevent cheating in online quizzes?

Combine multiple strategies: randomize question order and answer choices for each participant, set strict time limits per question (preventing Googling), use question banks large enough that no two participants see the same set, and monitor submission timing patterns. For high-stakes exams, consider requiring proctoring software or conducting assessments in controlled environments.

### What's the difference between a quiz platform and an LMS?

A quiz platform focuses exclusively on creating and delivering quizzes. An LMS (Learning Management System) like Moodle or Canvas includes quizzes as one feature among many — course organization, content delivery, grading, discussion forums, and student management. If you only need quizzes, a dedicated quiz platform is simpler to deploy and manage. If you need a complete learning environment, choose an LMS.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Quiz & Trivia Platforms: Open Trivia vs Quizmaster vs PHPQuiz 2026",
  "description": "Compare three open-source self-hosted quiz and trivia platforms: Open Trivia Database for real-time multiplayer, Quizmaster for embeddable widgets, and phpQuiz for structured assessments. Includes Docker Compose setups and deployment guidance.",
  "datePublished": "2026-06-19",
  "dateModified": "2026-06-19",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
