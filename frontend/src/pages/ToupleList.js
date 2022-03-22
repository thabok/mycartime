import React, { Component } from 'react';

class ToupleList extends Component {

    constructor(props) {
        super()
        this.state = {
            parties : this.sortTouples(props.touples, props.schoolbound)
        }
    }

    componentDidMount() {}

    render() {
        return (
            <ul>
                {this.state.parties.map((party, index) => {
                    if (this.props.filterForPerson && this.props.filterForPerson !== '') {
                        let found = party.driver.initials.toLowerCase().indexOf(this.props.filterForPerson.toLowerCase()) !== -1
                        if (!found) {
                            if (party.passengers) {
                                for (let i=0; i < party.passengers.length; i++) {
                                    if (party.passengers[i].initials.toLowerCase().indexOf(this.props.filterForPerson.toLowerCase()) !== -1) {
                                        found = true
                                        break
                                    }
                                }
                            }
                        }
                        if (!found) return null
                    }
                    return (this.getListItem(party, index))
                })}
            </ul>
        );
    }

    getListItem(party, index) {
        let passengerStrings = []
        for (let i=0; i < party.passengers.length; i++) {
            let p = party.passengers[i]
            passengerStrings.push(p.firstName + " (" + p.initials + ")")
        }
        return (<li key={index}>
            [{this.timeToString(party.time)}] <b>{party.isDesignatedDriver ? "*" : " "}{party.driver.firstName + " (" + party.driver.initials + ")"}</b> {(party.passengers.length > 0 ? " - " + passengerStrings.join(" - ") : "" )}
        </li>)
    }

    timeToString(time) {
        let hh = Math.floor(time / 100)
        hh = hh < 10 ? "0" + hh : "" + hh
        let mm = time % 100
        mm = mm < 10 ? "0" + mm : "" + mm
        return (hh + ":" + mm + "h")
    }

    sortTouples(unsortedTouples, schoolbound) {
        let parties = []
        for (let i=0; i < unsortedTouples.length; i++) {
            const touple = unsortedTouples[i]
            let party = null
            if (schoolbound) {
                party = touple.partyThere
            } else {
                party = touple.partyBack
            }
            party.isDesignatedDriver = touple.isDesignatedDriver
            parties.push(party)
        }
        parties.sort((a, b) => a.time < b.time ? -1 : 1)
        return parties
    }
}

export default ToupleList;
