async function waitForLogin() {
  while (true) {
    const res = await fetch("/api/session");
    const data = await res.json();
    if (data.logged_in) {
      return data.username;
    }
    await new Promise((r) => setTimeout(r, 500)); // wait 500ms
  }
}

$(document).ready(async function () {
  await (async () => {
    const language = "en";
    var card_data = {};

    await waitForLogin();

    try {
      card_data = await $.ajax({
        url: `/api/localization/${language}/cards`,
        method: "GET",
        dataType: "json",
      });

      const myDemoCards = [
        {
          title: "Ace",
          text: "Big Value",
          img: "https://via.placeholder.com/150/FF0000/FFFFFF?text=A",
        },
        {
          title: "King",
          text: "The Ruler",
          img: "https://via.placeholder.com/150/0000FF/FFFFFF?text=K",
        },
        {
          title: "Queen",
          text: "Tactician",
          img: "https://via.placeholder.com/150/008000/FFFFFF?text=Q",
        },
        {
          title: "Jack",
          text: "The Knave",
          img: "https://via.placeholder.com/150/FFFF00/000000?text=J",
        },
        {
          title: "Ten",
          text: "Solid",
          img: "https://via.placeholder.com/150/800080/FFFFFF?text=10",
        },
      ];

      var array_card_data = _.values(card_data);

      // Trigger generation
      CardGenerationHelper.generateHandCards(array_card_data);

      const enemyCardCount = 5;
      CardGenerationHelper.generateEnemyHandCards(enemyCardCount);
    } catch (error) {
      console.error("Error fetching skills:", error);
      throw error;
    }
  })();
});
