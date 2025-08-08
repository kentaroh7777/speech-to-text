// X Spaces投稿検出ロジック
const findLatestSpacesPost = async (profileUrl) => {
  // プロフィールページにアクセス
  await page.goto(profileUrl);

  // 十分なコンテンツを読み込むまでスクロール
  let previousTweetCount = 0;
  let currentTweetCount = 0;
  let scrollAttempts = 0;
  const maxScrollAttempts = 20;

  do {
    previousTweetCount = currentTweetCount;
    window.scrollTo(0, document.body.scrollHeight);
    await new Promise(resolve => setTimeout(resolve, 3000));
    currentTweetCount = document.querySelectorAll('[data-testid="tweet"], article').length;
    scrollAttempts++;
  } while (currentTweetCount > previousTweetCount && scrollAttempts < maxScrollAttempts);

  // X Spaces検出パターン
  const spacesPatterns = [
    {pattern: /ホスト/, name: "Host", weight: 3},
    {pattern: /録音を再生/, name: "Play Recording", weight: 5},
    {pattern: /\d+\s*人がリスニング/, name: "Listening Count", weight: 4},
    {pattern: /リプレイ/, name: "Replay", weight: 3},
    {pattern: /\d{1,2}:\d{2}/, name: "Duration", weight: 2},
    {pattern: /#\d+/, name: "Episode Number", weight: 1},
    {pattern: /スペース/i, name: "Spaces JP", weight: 2},
    {pattern: /spaces/i, name: "Spaces EN", weight: 2}
  ];

  // 全投稿を解析
  const tweets = Array.from(document.querySelectorAll('[data-testid="tweet"], article'));
  const spacesPosts = [];

  tweets.forEach((tweet, index) => {
    const tweetText = tweet.innerText;
    let totalWeight = 0;
    const matchedPatterns = [];

    spacesPatterns.forEach((patternObj) => {
      if (patternObj.pattern.test(tweetText)) {
        matchedPatterns.push(patternObj.name);
        totalWeight += patternObj.weight;
      }
    });

    // 重みが一定値以上の場合にSpaces投稿と判定
    if (totalWeight >= 5) {
      const tweetLinks = Array.from(tweet.querySelectorAll('a[href*="/status/"]'));
      const tweetUrl = tweetLinks.length > 0 ? tweetLinks[0].href : '';

      spacesPosts.push({
        url: tweetUrl,
        text: tweetText,
        weight: totalWeight,
        patterns: matchedPatterns,
        index: index
      });
    }
  });

  // 重みの高い順、新しい順でソート
  spacesPosts.sort((a, b) => {
    if (b.weight !== a.weight) return b.weight - a.weight;
    return a.index - b.index;
  });

  return spacesPosts.length > 0 ? spacesPosts[0].url : null;
};