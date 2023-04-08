# CS50: Finance

This project was completed as part of Harvard's CS50 on EdX. Additional information about this project are available <a href="https://cs50.harvard.edu/x/2023/psets/9/finance/">here</a>.

The project involved creating a website that allows users to engage in imaginary stock trading by creating an account, buying, and selling stocks.

To implement the functionality required for this project, I developed the following features:

<ul>
<li>Register: This feature enables users to register on the website by submitting their username and password. The information is then stored in a sqlite 3 database.</li>
<li>Quote: Users can use this feature to look up the price of a stock by entering its symbol.</li>
<li>Buy: This feature allows users to purchase imaginary stocks, which are then saved in the database along with updates to their available funds.</li>
<li>Index: Users can view a summary table in HTML format that displays their current funds and stocks.</li>
<li>Sell: Users can sell stocks using this feature, which removes the stocks from the database and updates their available funds accordingly.</li>
<li>History: This feature enables users to view a table in HTML format that displays their transaction history.</li>
</ul>

It's worth noting that all code not related to the features mentioned above was provided by CS50.
